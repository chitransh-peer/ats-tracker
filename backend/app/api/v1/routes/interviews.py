import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.api.v1.routes._application_refs import with_application_refs
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.core.pagination import PageParams, page_params, paginate
from app.schemas.auth import CurrentUser
from app.schemas.interview import (
    ConsolidatedFeedbackRead,
    InterviewCreate,
    InterviewFeedbackCreate,
    InterviewFeedbackRead,
    InterviewRead,
    InterviewUpdate,
)
from app.services.audit.service import record as record_audit
from app.services.interviews import service as interview_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


class InterviewSummary(BaseModel):
    scheduled: int
    completed: int
    awaiting_feedback: int


@router.get("", response_model=list[InterviewRead])
def list_interviews(
    response: Response,
    application_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    upcoming: bool = False,
    pagination: PageParams = Depends(page_params),
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[InterviewRead]:
    """One page of interviews, each with its candidate and job named; the
    total rides on X-Total-Count."""
    query = interview_service.build_interviews_query(
        current_user.organization_id,
        application_id=application_id,
        candidate_id=candidate_id,
        status=status,
        upcoming=upcoming,
        viewer=current_user,
    )
    interviews, total = paginate(db, query, pagination)
    response.headers["X-Total-Count"] = str(total)
    return with_application_refs(db, interviews, InterviewRead)


@router.get("/summary", response_model=InterviewSummary)
def interview_summary(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> InterviewSummary:
    return InterviewSummary(**interview_service.interview_summary(db, current_user.organization_id, viewer=current_user))


@router.post("", response_model=InterviewRead, status_code=201)
def create_interview(
    payload: InterviewCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> InterviewRead:
    interview = interview_service.create_interview(
        db, organization_id=current_user.organization_id, actor_id=current_user.id, **payload.model_dump()
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.INTERVIEW_SCHEDULED.value,
        resource_type="interview",
        resource_id=str(interview.id),
    )
    db.commit()
    return interview


@router.get("/{interview_id}", response_model=InterviewRead)
def get_interview(
    interview_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> InterviewRead:
    interview = interview_service.get_interview(db, current_user.organization_id, interview_id, viewer=current_user)
    return with_application_refs(db, [interview], InterviewRead)[0]


@router.patch("/{interview_id}", response_model=InterviewRead)
def update_interview(
    interview_id: uuid.UUID,
    payload: InterviewUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> InterviewRead:
    interview = interview_service.get_interview(db, current_user.organization_id, interview_id, viewer=current_user)
    interview = interview_service.update_interview(
        db, interview, actor_id=current_user.id, **payload.model_dump(exclude_unset=True)
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.INTERVIEW_UPDATED.value,
        resource_type="interview",
        resource_id=str(interview.id),
    )
    db.commit()
    return interview


@router.post("/{interview_id}/feedback", response_model=InterviewFeedbackRead, status_code=201)
def submit_feedback(
    interview_id: uuid.UUID,
    payload: InterviewFeedbackCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> InterviewFeedbackRead:
    interview = interview_service.get_interview(db, current_user.organization_id, interview_id, viewer=current_user)
    feedback = interview_service.submit_feedback(
        db,
        interview,
        submitted_by=current_user.id,
        rating=payload.rating,
        recommendation=payload.recommendation,
        notes=payload.notes,
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.INTERVIEW_FEEDBACK_SUBMITTED.value,
        resource_type="interview",
        resource_id=str(interview.id),
    )
    db.commit()
    return feedback


@router.get("/{interview_id}/consolidated-feedback", response_model=ConsolidatedFeedbackRead)
def consolidated_feedback(
    interview_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.INTERVIEW, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> ConsolidatedFeedbackRead:
    interview = interview_service.get_interview(db, current_user.organization_id, interview_id, viewer=current_user)
    return interview_service.consolidated_feedback(db, interview)
