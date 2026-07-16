import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.audit import AuditLogRead
from app.schemas.auth import CurrentUser
from app.services.audit.service import list_logs

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def get_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AUDIT_LOG, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[AuditLogRead]:
    return list_logs(
        db,
        current_user.organization_id,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
    )
