import uuid

from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import RoleName
from app.core.exceptions import ConflictError, NotFoundError
from app.core.scoping import scoped_roles
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.candidate import Candidate
from app.db.models.interview import Interview, InterviewPanelMember
from app.db.models.job import Job
from app.db.models.user import User
from app.schemas.auth import CurrentUser
from app.services.jobs.service import get_job


def _scope_filter(query, viewer: CurrentUser | None):
    if viewer is None:
        return query
    scopes = scoped_roles(viewer.roles)
    if not scopes:
        return query

    conditions = []
    if RoleName.HIRING_MANAGER.value in scopes:
        conditions.append(Application.job_id.in_(select(Job.id).where(Job.hiring_manager_id == viewer.id)))
    if RoleName.INTERVIEWER.value in scopes:
        conditions.append(
            Application.id.in_(
                select(Interview.application_id)
                .join(InterviewPanelMember, InterviewPanelMember.interview_id == Interview.id)
                .where(InterviewPanelMember.user_id == viewer.id)
            )
        )
    if RoleName.CANDIDATE.value in scopes:
        # A candidate's login and their candidate record share an email address
        # within the organization; that is the only link between the two.
        conditions.append(
            Application.candidate_id.in_(
                select(Candidate.id)
                .join(
                    User,
                    (func.lower(User.email) == func.lower(Candidate.email))
                    & (User.organization_id == Candidate.organization_id),
                )
                .where(User.id == viewer.id, Candidate.email.is_not(None))
            )
        )
    # false() first: with no condition for this viewer's roles, nothing matches.
    return query.where(or_(false(), *conditions))


def check_viewer_may_apply(
    db: Session, organization_id: uuid.UUID, *, candidate_id: uuid.UUID, job_id: uuid.UUID, viewer: CurrentUser
) -> None:
    """A scoped viewer may only apply as themselves, to a job they can see.

    Only the Candidate role is both scoped and allowed to create applications;
    without this it could file an application for any candidate record."""
    if not scoped_roles(viewer.roles):
        return
    own_candidate = db.scalar(
        select(Candidate.id)
        .join(
            User,
            (func.lower(User.email) == func.lower(Candidate.email)) & (User.organization_id == Candidate.organization_id),
        )
        .where(User.id == viewer.id, Candidate.id == candidate_id, Candidate.organization_id == organization_id)
    )
    if own_candidate is None:
        raise NotFoundError("Candidate not found")
    get_job(db, organization_id, job_id, viewer=viewer)


def create_application(
    db: Session,
    *,
    organization_id: uuid.UUID,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    source: str | None,
) -> Application:
    existing = db.scalar(select(Application).where(Application.candidate_id == candidate_id, Application.job_id == job_id))
    if existing is not None:
        raise ConflictError("This candidate has already applied to this job")

    job = db.get(Job, job_id)
    if job is None or job.organization_id != organization_id:
        raise NotFoundError("Job not found")

    first_stage = job.stage_template.stages[0] if job.stage_template and job.stage_template.stages else None

    application = Application(
        organization_id=organization_id,
        candidate_id=candidate_id,
        job_id=job_id,
        current_stage_id=first_stage.id if first_stage else None,
        source=source,
    )
    db.add(application)
    db.flush()

    db.add(
        ApplicationStageHistory(
            application_id=application.id,
            from_stage_id=None,
            to_stage_id=first_stage.id if first_stage else None,
            changed_by=None,
            note="Application submitted",
        )
    )
    db.commit()
    db.refresh(application)
    return application


def get_application(
    db: Session, organization_id: uuid.UUID, application_id: uuid.UUID, *, viewer: CurrentUser | None = None
) -> Application:
    query = select(Application).where(Application.id == application_id, Application.organization_id == organization_id)
    application = db.scalar(_scope_filter(query, viewer))
    if application is None:
        raise NotFoundError("Application not found")
    return application


def _search_filter(search: str | None):
    """Case-insensitive "contains" on the candidate's name or the job title."""
    if not search or not search.strip():
        return None
    like = f"%{search.strip()}%"
    return or_(
        Application.candidate_id.in_(select(Candidate.id).where(Candidate.full_name.ilike(like))),
        Application.job_id.in_(select(Job.id).where(Job.title.ilike(like))),
    )


def build_applications_query(
    organization_id: uuid.UUID,
    *,
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    viewer: CurrentUser | None = None,
):
    """Filters + scoping only, unexecuted — see the equivalent in the
    candidates service for why this is split out from execution."""
    query = select(Application).where(Application.organization_id == organization_id)
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    if candidate_id is not None:
        query = query.where(Application.candidate_id == candidate_id)
    if status is not None:
        query = query.where(Application.status == status)
    condition = _search_filter(search)
    if condition is not None:
        query = query.where(condition)
    query = _scope_filter(query, viewer)
    return query.order_by(Application.applied_at.desc(), Application.id)


def application_labels(db: Session, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Candidate and job, with names, for a page of applications in one query.

    Lists of applications, interviews, offers and onboarding cases carry these
    so the page never has to load every candidate and job to look names up.
    """
    if not application_ids:
        return {}
    rows = db.execute(
        select(Application.id, Application.candidate_id, Candidate.full_name, Application.job_id, Job.title, Job.req_id)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .join(Job, Job.id == Application.job_id)
        .where(Application.id.in_(set(application_ids)))
    ).all()
    return {
        row[0]: {
            "candidate_id": row[1],
            "candidate_name": row[2],
            "job_id": row[3],
            "job_title": row[4],
            "job_req_id": row[5],
        }
        for row in rows
    }


def application_options(
    db: Session,
    organization_id: uuid.UUID,
    *,
    search: str | None = None,
    status: str | None = None,
    ids: list[uuid.UUID] | None = None,
    limit: int = 20,
    viewer: CurrentUser | None = None,
) -> list[tuple[uuid.UUID, str, str]]:
    """(id, candidate name, job title) for a type-to-search picker: the first
    `limit` matches, or the named `ids` so a picker can label its value."""
    query = (
        select(Application.id, Candidate.full_name, Job.title)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .join(Job, Job.id == Application.job_id)
        .where(Application.organization_id == organization_id)
    )
    if ids:
        query = query.where(Application.id.in_(ids))
    else:
        if status:
            query = query.where(Application.status == status)
        if search and search.strip():
            like = f"%{search.strip()}%"
            query = query.where(or_(Candidate.full_name.ilike(like), Job.title.ilike(like)))
    query = _scope_filter(query, viewer).order_by(Application.applied_at.desc(), Application.id).limit(limit)
    return [(row[0], row[1], row[2]) for row in db.execute(query).all()]


# The unpaged path, for callers that pass a narrow filter (one candidate's or
# one job's applications). Every list page pages instead; the cap only bounds
# the worst case of a caller that forgets to.
_UNPAGINATED_SAFETY_LIMIT = 2000


def list_applications(
    db: Session,
    organization_id: uuid.UUID,
    *,
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    viewer: CurrentUser | None = None,
) -> list[Application]:
    query = build_applications_query(organization_id, job_id=job_id, candidate_id=candidate_id, status=status, viewer=viewer)
    return list(db.scalars(query.limit(_UNPAGINATED_SAFETY_LIMIT)).unique().all())


def get_timeline(db: Session, application: Application) -> list[ApplicationStageHistory]:
    return list(
        db.scalars(
            select(ApplicationStageHistory)
            .where(ApplicationStageHistory.application_id == application.id)
            .order_by(ApplicationStageHistory.created_at)
        ).all()
    )
