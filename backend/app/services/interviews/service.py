import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import RoleName
from app.core.exceptions import NotFoundError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.interview import Interview, InterviewFeedback, InterviewPanelMember
from app.db.models.job import Job
from app.schemas.auth import CurrentUser


def _scope_filter(query, viewer: CurrentUser | None):
    if viewer is None:
        return query
    scopes = scoped_roles(viewer.roles)
    if not scopes:
        return query

    conditions = []
    if RoleName.HIRING_MANAGER.value in scopes:
        conditions.append(
            Interview.application_id.in_(
                select(Application.id).join(Job, Job.id == Application.job_id).where(Job.hiring_manager_id == viewer.id)
            )
        )
    if RoleName.INTERVIEWER.value in scopes:
        conditions.append(
            Interview.id.in_(select(InterviewPanelMember.interview_id).where(InterviewPanelMember.user_id == viewer.id))
        )
    return query.where(or_(*conditions))


def _load(query):
    return query.options(selectinload(Interview.panel_members), selectinload(Interview.feedback_entries))


def create_interview(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    application_id: uuid.UUID,
    round_name: str,
    mode: str,
    scheduled_at: datetime,
    panel_user_ids: list[uuid.UUID],
    primary_interviewer_id: uuid.UUID | None,
) -> Interview:
    application = db.get(Application, application_id)
    if application is None or application.organization_id != organization_id:
        raise NotFoundError("Application not found")

    interview = Interview(
        organization_id=organization_id,
        application_id=application_id,
        round_name=round_name,
        mode=mode,
        scheduled_at=scheduled_at,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(interview)
    db.flush()

    for user_id in dict.fromkeys(panel_user_ids):
        db.add(
            InterviewPanelMember(interview_id=interview.id, user_id=user_id, is_primary=(user_id == primary_interviewer_id))
        )
    db.commit()
    db.refresh(interview)
    return interview


def get_interview(
    db: Session, organization_id: uuid.UUID, interview_id: uuid.UUID, *, viewer: CurrentUser | None = None
) -> Interview:
    query = _load(select(Interview)).where(Interview.id == interview_id, Interview.organization_id == organization_id)
    interview = db.scalar(_scope_filter(query, viewer))
    if interview is None:
        raise NotFoundError("Interview not found")
    return interview


def list_interviews(
    db: Session,
    organization_id: uuid.UUID,
    *,
    application_id: uuid.UUID | None = None,
    status: str | None = None,
    viewer: CurrentUser | None = None,
) -> list[Interview]:
    query = _load(select(Interview)).where(Interview.organization_id == organization_id)
    if application_id is not None:
        query = query.where(Interview.application_id == application_id)
    if status is not None:
        query = query.where(Interview.status == status)
    query = _scope_filter(query, viewer)
    query = query.order_by(Interview.scheduled_at)
    return list(db.scalars(query).all())


def update_interview(db: Session, interview: Interview, *, actor_id: uuid.UUID | None, **fields) -> Interview:
    for key, value in fields.items():
        if value is not None:
            setattr(interview, key, value)
    interview.updated_by = actor_id
    db.commit()
    db.refresh(interview)
    return interview


def submit_feedback(
    db: Session,
    interview: Interview,
    *,
    submitted_by: uuid.UUID | None,
    rating: int,
    recommendation: str,
    notes: str | None,
) -> InterviewFeedback:
    feedback = InterviewFeedback(
        interview_id=interview.id, submitted_by=submitted_by, rating=rating, recommendation=recommendation, notes=notes
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def consolidated_feedback(db: Session, interview: Interview) -> dict:
    entries = interview.feedback_entries
    ratings = [e.rating for e in entries]
    recommendation_counts: dict[str, int] = {}
    for entry in entries:
        recommendation_counts[entry.recommendation] = recommendation_counts.get(entry.recommendation, 0) + 1
    return {
        "interview_id": interview.id,
        "average_rating": sum(ratings) / len(ratings) if ratings else None,
        "recommendation_counts": recommendation_counts,
        "feedback_entries": entries,
    }
