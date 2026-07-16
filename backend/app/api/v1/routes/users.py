import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.user import AssignRolesRequest, UserRead, UserUpdate
from app.services.audit.service import record as record_audit
from app.services.auth import service as auth_service
from app.services.users import service as user_service

router = APIRouter(prefix="/users", tags=["users"])


class InviteUserRequest(BaseModel):
    email: str
    role_name: str


class InviteUserResponse(BaseModel):
    email: str
    role_name: str
    invitation_token: str


def _to_read(user) -> UserRead:
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
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
    token = auth_service.create_invitation(
        db,
        organization_id=current_user.organization_id,
        email=payload.email,
        role_name=payload.role_name,
        invited_by=current_user.id,
    )
    return InviteUserResponse(email=payload.email, role_name=payload.role_name, invitation_token=token)


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
