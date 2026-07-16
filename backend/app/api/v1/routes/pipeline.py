from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.pipeline import StageTemplateRead
from app.services.pipeline.service import get_default_stage_template

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/stages", response_model=StageTemplateRead)
def get_default_stages(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> StageTemplateRead:
    template = get_default_stage_template(db, current_user.organization_id)
    return template
