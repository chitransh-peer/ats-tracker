import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_super_admin
from app.core.pagination import PageParams, page_params, paginate
from app.schemas.audit import AuditLogRead, AuditUserSummary
from app.schemas.auth import CurrentUser
from app.services.audit.service import build_logs_query, summarize_by_user

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def get_audit_logs(
    response: Response,
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    pagination: PageParams = Depends(page_params),
    current_user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
) -> list[AuditLogRead]:
    # The audit trail grows fastest of any table in the system, so this is the
    # one endpoint that gets paginated by default rather than opt-in.
    query = build_logs_query(
        current_user.organization_id, action=action, resource_type=resource_type, actor_user_id=actor_user_id
    )
    logs, total = paginate(db, query, pagination)
    response.headers["X-Total-Count"] = str(total)
    return logs


@router.get("/by-user", response_model=list[AuditUserSummary])
def get_audit_summary_by_user(
    current_user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
) -> list[AuditUserSummary]:
    return summarize_by_user(db, current_user.organization_id)
