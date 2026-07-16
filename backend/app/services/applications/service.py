import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.job import Job


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


def get_application(db: Session, organization_id: uuid.UUID, application_id: uuid.UUID) -> Application:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id, Application.organization_id == organization_id
        )
    )
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
) -> list[Application]:
    query = select(Application).where(Application.organization_id == organization_id)
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    if candidate_id is not None:
        query = query.where(Application.candidate_id == candidate_id)
    if status is not None:
        query = query.where(Application.status == status)
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
