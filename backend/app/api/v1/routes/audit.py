import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_super_admin
from app.schemas.audit import AuditLogRead, AuditUserSummary
from app.schemas.auth import CurrentUser
from app.services.audit.service import list_logs, summarize_by_user

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def get_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
) -> list[AuditLogRead]:
    return list_logs(
        db,
        current_user.organization_id,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
    )


@router.get("/by-user", response_model=list[AuditUserSummary])
def get_audit_summary_by_user(
    current_user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
) -> list[AuditUserSummary]:
    return summarize_by_user(db, current_user.organization_id)
