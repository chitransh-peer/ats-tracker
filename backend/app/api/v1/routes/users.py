import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission, require_super_admin
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.user import AssignRolesRequest, UserRead, UserUpdate
from app.services.audit.service import record as record_audit
from app.services.auth import service as auth_service
from app.services.mail import messages as mail_messages
from app.services.organizations import service as organization_service
from app.services.users import service as user_service
from app.workers.dispatch import dispatch
from app.workers.tasks.mail import send_email_task

router = APIRouter(prefix="/users", tags=["users"])


class InviteUserRequest(BaseModel):
    email: str
    full_name: str
    role_name: str


class InviteUserResponse(BaseModel):
    """`temporary_password` is returned once, at creation, and is not stored in
    recoverable form. It is echoed back so an admin can read it out to the
    person directly when mail is unconfigured or the invite lands in spam."""

    email: str
    full_name: str
    role_name: str
    temporary_password: str
    expires_at: datetime


def _to_read(user) -> UserRead:
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        roles=user_service.role_names_for_user(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.USER, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[UserRead]:
    users = user_service.list_users(db, current_user.organization_id)
    return [_to_read(u) for u in users]


@router.post("", response_model=InviteUserResponse, status_code=201)
def invite_user(
    payload: InviteUserRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.USER, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> InviteUserResponse:
    user, temporary_password = auth_service.invite_user(
        db,
        organization_id=current_user.organization_id,
        email=payload.email,
        full_name=payload.full_name,
        role_name=payload.role_name,
        invited_by=current_user.id,
    )

    organization = organization_service.get_organization(db, current_user.organization_id)
    subject, text_body, html_body = mail_messages.invitation(
        full_name=user.full_name,
        email=user.email,
        temporary_password=temporary_password,
        organization_name=organization.name,
        role_name=payload.role_name,
        expires_at=user.temp_password_expires_at,
    )
    # allow_inline: this mail carries the only copy of the temporary password.
    # If it does not go out, the invitation is useless, so it is worth the wait.
    dispatch(send_email_task, user.email, subject, text_body, html_body, allow_inline=True)

    return InviteUserResponse(
        email=user.email,
        full_name=user.full_name,
        role_name=payload.role_name,
        temporary_password=temporary_password,
        expires_at=user.temp_password_expires_at,
    )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.USER, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> UserRead:
    user = user_service.get_user_by_id(db, current_user.organization_id, user_id)
    return _to_read(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.USER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> UserRead:
    user = user_service.get_user_by_id(db, current_user.organization_id, user_id)
    user = user_service.update_user(db, user, full_name=payload.full_name, is_active=payload.is_active)
    return _to_read(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
) -> None:
    """Permanently delete a user. Super Admin only, and irreversible.

    Gated above the ordinary user:delete permission on purpose: deactivation
    covers the everyday case of someone leaving, and this does not.
    """
    user = user_service.get_user_by_id(db, current_user.organization_id, user_id)

    # Recorded before the row goes, and carrying the identity, because the
    # deleted user's other audit entries lose their author to ON DELETE SET
    # NULL. This one entry is what preserves the trace.
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.USER_DELETED.value,
        resource_type="user",
        resource_id=str(user.id),
        metadata={
            "email": user.email,
            "full_name": user.full_name,
            "roles": user_service.role_names_for_user(user),
        },
    )
    user_service.delete_user(db, user, acting_user_id=current_user.id)


@router.post("/{user_id}/roles", response_model=UserRead)
def assign_roles(
    user_id: uuid.UUID,
    payload: AssignRolesRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.USER, PermissionAction.MANAGE)),
    db: Session = Depends(get_db_session),
) -> UserRead:
    user = user_service.get_user_by_id(db, current_user.organization_id, user_id)
    user = user_service.assign_roles(db, user, payload.role_names)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action="role_assigned",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"role_names": payload.role_names},
    )
    db.commit()
    return _to_read(user)
