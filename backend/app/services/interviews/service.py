import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, false, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import InterviewStatus, RoleName
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.interview import Interview, InterviewFeedback, InterviewPanelMember
from app.db.models.job import Job
from app.db.models.user import User
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
    # false() first: with no condition for this viewer's roles, nothing matches.
    return query.where(or_(false(), *conditions))


def _load(query):
    return query.options(selectinload(Interview.panel_members), selectinload(Interview.feedback_entries))


def _set_panel(
    db: Session,
    interview: Interview,
    organization_id: uuid.UUID,
    panel_user_ids: list[uuid.UUID],
    primary_interviewer_id: uuid.UUID | None,
) -> None:
    """Replaces the panel with these users, who must be active members of the
    organization; the primary interviewer, when given, must be on the panel."""
    user_ids = list(dict.fromkeys(panel_user_ids))
    if primary_interviewer_id is not None and primary_interviewer_id not in user_ids:
        user_ids.insert(0, primary_interviewer_id)
    if user_ids:
        found = set(
            db.scalars(
                select(User.id).where(
                    User.id.in_(user_ids),
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        )
        if len(found) != len(user_ids):
            raise ValidationAppError("Every interviewer must be an active user in your organization")
    if primary_interviewer_id is None and user_ids:
        primary_interviewer_id = user_ids[0]
    interview.panel_members.clear()
    db.flush()
    for user_id in user_ids:
        interview.panel_members.append(InterviewPanelMember(user_id=user_id, is_primary=(user_id == primary_interviewer_id)))


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
    timezone: str | None = None,
    duration_minutes: int | None = None,
    meeting_link: str | None = None,
    location: str | None = None,
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
        timezone=timezone,
        duration_minutes=duration_minutes,
        meeting_link=meeting_link,
        location=location,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(interview)
    db.flush()
    _set_panel(db, interview, organization_id, panel_user_ids, primary_interviewer_id)
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


def build_interviews_query(
    organization_id: uuid.UUID,
    *,
    application_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    upcoming: bool = False,
    viewer: CurrentUser | None = None,
) -> Select:
    """Filtered, scoped interview query; the caller pages it.

    Newest first, so the first page is this week rather than the oldest
    interview on record. `upcoming` narrows to scheduled interviews still
    ahead and orders them soonest first.
    """
    query = _load(select(Interview)).where(Interview.organization_id == organization_id)
    if application_id is not None:
        query = query.where(Interview.application_id == application_id)
    if candidate_id is not None:
        query = query.where(
            Interview.application_id.in_(select(Application.id).where(Application.candidate_id == candidate_id))
        )
    if status is not None:
        query = query.where(Interview.status == status)
    query = _scope_filter(query, viewer)
    if upcoming:
        query = query.where(Interview.status == InterviewStatus.SCHEDULED.value, Interview.scheduled_at >= datetime.now(UTC))
        return query.order_by(Interview.scheduled_at, Interview.id)
    return query.order_by(Interview.scheduled_at.desc(), Interview.id)


def interview_summary(db: Session, organization_id: uuid.UUID, *, viewer: CurrentUser | None = None) -> dict[str, int]:
    """Counts for the list page's stat cards, within the viewer's scope."""
    no_feedback = ~select(InterviewFeedback.id).where(InterviewFeedback.interview_id == Interview.id).exists()
    completed = Interview.status == InterviewStatus.COMPLETED.value
    query = select(
        func.count(Interview.id).filter(Interview.status == InterviewStatus.SCHEDULED.value),
        func.count(Interview.id).filter(completed),
        func.count(Interview.id).filter(completed & no_feedback),
    ).where(Interview.organization_id == organization_id)
    scheduled, completed_count, awaiting = db.execute(_scope_filter(query, viewer)).one()
    return {"scheduled": scheduled, "completed": completed_count, "awaiting_feedback": awaiting}


# Optional details a scheduler may clear by sending null.
_CLEARABLE = {"timezone", "duration_minutes", "meeting_link", "location"}


def update_interview(db: Session, interview: Interview, *, actor_id: uuid.UUID | None, **fields) -> Interview:
    panel_user_ids = fields.pop("panel_user_ids", None)
    primary_interviewer_id = fields.pop("primary_interviewer_id", None)
    if panel_user_ids is not None:
        _set_panel(db, interview, interview.organization_id, panel_user_ids, primary_interviewer_id)
    for key, value in fields.items():
        if value is not None or key in _CLEARABLE:
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
