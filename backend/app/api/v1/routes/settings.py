from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.organization import OrganizationRead, OrganizationSettingsUpdate
from app.services.audit.service import record as record_audit
from app.services.organizations import service as organization_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/organization", response_model=OrganizationRead)
def get_organization_settings(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.SETTINGS, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    return organization_service.get_organization(db, current_user.organization_id)


@router.patch("/organization", response_model=OrganizationRead)
def update_organization_settings(
    payload: OrganizationSettingsUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.SETTINGS, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    org = organization_service.get_organization(db, current_user.organization_id)
    org = organization_service.update_settings(db, org, **payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.SETTINGS_CHANGED.value,
        resource_type="organization",
        resource_id=str(org.id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    return org
