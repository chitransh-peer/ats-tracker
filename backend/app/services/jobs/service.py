import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, JobStatus
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.application import Application
from app.db.models.job import Job
from app.db.models.pipeline_stage import StageTemplateStage
from app.services.pipeline.service import seed_default_stage_template
from app.utils.text import slugify

_VALID_TRANSITIONS: dict[str, set[str]] = {
    JobStatus.DRAFT.value: {JobStatus.ACTIVE.value, JobStatus.CANCELLED.value},
    JobStatus.ACTIVE.value: {JobStatus.DRAFT.value, JobStatus.ON_HOLD.value, JobStatus.CLOSED.value, JobStatus.CANCELLED.value},
    JobStatus.ON_HOLD.value: {JobStatus.ACTIVE.value, JobStatus.CLOSED.value, JobStatus.CANCELLED.value},
    JobStatus.CLOSED.value: set(),
    JobStatus.CANCELLED.value: set(),
}


def _generate_req_id(db: Session, organization_id: uuid.UUID) -> str:
    count = db.scalar(select(func.count(Job.id)).where(Job.organization_id == organization_id)) or 0
    return f"REQ-{datetime.now(timezone.utc).year}{count + 1:04d}"


def _generate_slug(title: str) -> str:
    return f"{slugify(title)}-{secrets.token_hex(3)}"


def create_job(db: Session, *, organization_id: uuid.UUID, actor_id: uuid.UUID | None, **fields) -> Job:
    stage_template = seed_default_stage_template(db, organization_id)

    job = Job(
        organization_id=organization_id,
        req_id=_generate_req_id(db, organization_id),
        slug=_generate_slug(fields["title"]),
        stage_template_id=stage_template.id,
        status=JobStatus.DRAFT.value,
        created_by=actor_id,
        updated_by=actor_id,
        **fields,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.organization_id == organization_id, Job.deleted_at.is_(None))
    )
    if job is None:
        raise NotFoundError("Job not found")
    return job


def list_jobs(
    db: Session,
    organization_id: uuid.UUID,
    *,
    status: str | None = None,
    department: str | None = None,
    client_id: uuid.UUID | None = None,
    recruiter_id: uuid.UUID | None = None,
) -> list[Job]:
    query = select(Job).where(Job.organization_id == organization_id, Job.deleted_at.is_(None))
    if status is not None:
        query = query.where(Job.status == status)
    if department is not None:
        query = query.where(Job.department == department)
    if client_id is not None:
        query = query.where(Job.client_id == client_id)
    if recruiter_id is not None:
        query = query.where(Job.recruiter_id == recruiter_id)
    query = query.order_by(Job.created_at.desc())
    return list(db.scalars(query).all())


def update_job(db: Session, job: Job, *, actor_id: uuid.UUID | None, **fields) -> Job:
    for key, value in fields.items():
        if value is not None:
            setattr(job, key, value)
    job.updated_by = actor_id
    db.commit()
    db.refresh(job)
    return job


def _transition(db: Session, job: Job, *, to_status: str, actor_id: uuid.UUID | None) -> Job:
    allowed = _VALID_TRANSITIONS.get(job.status, set())
    if to_status not in allowed:
        raise ValidationAppError(f"Cannot move job from '{job.status}' to '{to_status}'")

    job.status = to_status
    job.updated_by = actor_id
    if to_status == JobStatus.ACTIVE.value and job.posted_at is None:
        job.posted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def publish_job(db: Session, job: Job, *, actor_id: uuid.UUID | None) -> Job:
    return _transition(db, job, to_status=JobStatus.ACTIVE.value, actor_id=actor_id)


def unpublish_job(db: Session, job: Job, *, actor_id: uuid.UUID | None) -> Job:
    return _transition(db, job, to_status=JobStatus.DRAFT.value, actor_id=actor_id)


def close_job(db: Session, job: Job, *, actor_id: uuid.UUID | None) -> Job:
    return _transition(db, job, to_status=JobStatus.CLOSED.value, actor_id=actor_id)


def hold_job(db: Session, job: Job, *, actor_id: uuid.UUID | None) -> Job:
    return _transition(db, job, to_status=JobStatus.ON_HOLD.value, actor_id=actor_id)


def cancel_job(db: Session, job: Job, *, actor_id: uuid.UUID | None) -> Job:
    return _transition(db, job, to_status=JobStatus.CANCELLED.value, actor_id=actor_id)


def job_stats(db: Session, job_id: uuid.UUID) -> dict[str, int]:
    applications_count = db.scalar(select(func.count(Application.id)).where(Application.job_id == job_id)) or 0
    hires_count = db.scalar(
        select(func.count(Application.id)).where(
            Application.job_id == job_id, Application.status == ApplicationStatus.HIRED.value
        )
    ) or 0
    shortlisted_count = db.scalar(
        select(func.count(Application.id))
        .join(StageTemplateStage, Application.current_stage_id == StageTemplateStage.id)
        .where(Application.job_id == job_id, StageTemplateStage.name == "Shortlisted")
    ) or 0
    return {
        "applications_count": applications_count,
        "shortlisted_count": shortlisted_count,
        "interviews_count": 0,
        "offers_count": 0,
        "hires_count": hires_count,
    }
