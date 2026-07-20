import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import RoleName
from app.core.exceptions import ConflictError, NotFoundError
from app.core.scoping import scoped_roles
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.interview import Interview, InterviewPanelMember
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
            Application.job_id.in_(select(Job.id).where(Job.hiring_manager_id == viewer.id))
        )
    if RoleName.INTERVIEWER.value in scopes:
        conditions.append(
            Application.id.in_(
                select(Interview.application_id)
                .join(InterviewPanelMember, InterviewPanelMember.interview_id == Interview.id)
                .where(InterviewPanelMember.user_id == viewer.id)
            )
        )
    return query.where(or_(*conditions))


def create_application(
    db: Session,
    *,
    organization_id: uuid.UUID,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    source: str | None,
) -> Application:
    existing = db.scalar(
        select(Application).where(Application.candidate_id == candidate_id, Application.job_id == job_id)
    )
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
    query = select(Application).where(
        Application.id == application_id, Application.organization_id == organization_id
    )
    application = db.scalar(_scope_filter(query, viewer))
    if application is None:
        raise NotFoundError("Application not found")
    return application


def list_applications(
    db: Session,
    organization_id: uuid.UUID,
    *,
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    viewer: CurrentUser | None = None,
) -> list[Application]:
    query = select(Application).where(Application.organization_id == organization_id)
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    if candidate_id is not None:
        query = query.where(Application.candidate_id == candidate_id)
    if status is not None:
        query = query.where(Application.status == status)
    query = _scope_filter(query, viewer)
    query = query.order_by(Application.applied_at.desc())
    return list(db.scalars(query).all())


def get_timeline(db: Session, application: Application) -> list[ApplicationStageHistory]:
    return list(
        db.scalars(
            select(ApplicationStageHistory)
            .where(ApplicationStageHistory.application_id == application.id)
            .order_by(ApplicationStageHistory.created_at)
        ).all()
    )
