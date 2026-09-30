import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.pipeline import PipelineBoardRead, StageTemplateRead
from app.services.pipeline.board import board
from app.services.pipeline.service import get_default_stage_template

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

_READ = require_permission(PermissionResource.PIPELINE, PermissionAction.READ)


@router.get("/stages", response_model=StageTemplateRead)
def get_default_stages(
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> StageTemplateRead:
    template = get_default_stage_template(db, current_user.organization_id)
    return template


@router.get("/board", response_model=PipelineBoardRead)
def get_board(
    job_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> PipelineBoardRead:
    """The board for every job, or for one. Counts are exact; cards stop at
    2,000 (the response says how many there are in all)."""
    return PipelineBoardRead(**board(db, current_user.organization_id, job_id=job_id, viewer=current_user))
