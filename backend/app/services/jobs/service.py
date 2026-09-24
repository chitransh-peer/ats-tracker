import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ApplicationStatus, JobStatus, RoleName
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.interview import Interview, InterviewPanelMember
from app.db.models.job import Job, JobCustomField, JobDocument, JobNote, JobSearchCriteria
from app.db.models.pipeline_stage import StageTemplateStage
from app.db.models.user import User
from app.schemas.auth import CurrentUser
from app.services.pipeline.service import seed_default_stage_template
from app.services.storage import service as storage_service
from app.utils.text import slugify


def _scope_filter(query, viewer: CurrentUser | None):
    if viewer is None:
        return query
    scopes = scoped_roles(viewer.roles)
    if not scopes:
        return query

    conditions = []
    if RoleName.HIRING_MANAGER.value in scopes:
        conditions.append(Job.hiring_manager_id == viewer.id)
    if RoleName.INTERVIEWER.value in scopes:
        conditions.append(
            Job.id.in_(
                select(Application.job_id)
                .join(Interview, Interview.application_id == Application.id)
                .join(InterviewPanelMember, InterviewPanelMember.interview_id == Interview.id)
                .where(InterviewPanelMember.user_id == viewer.id)
            )
        )
    return query.where(or_(*conditions))


_VALID_TRANSITIONS: dict[str, set[str]] = {
    JobStatus.DRAFT.value: {JobStatus.ACTIVE.value, JobStatus.CANCELLED.value},
    JobStatus.ACTIVE.value: {
        JobStatus.DRAFT.value,
        JobStatus.ON_HOLD.value,
        JobStatus.CLOSED.value,
        JobStatus.CANCELLED.value,
    },
    JobStatus.ON_HOLD.value: {JobStatus.ACTIVE.value, JobStatus.CLOSED.value, JobStatus.CANCELLED.value},
    JobStatus.CLOSED.value: set(),
    JobStatus.CANCELLED.value: set(),
}


def _generate_req_id(db: Session, organization_id: uuid.UUID) -> str:
    count = db.scalar(select(func.count(Job.id)).where(Job.organization_id == organization_id)) or 0
    return f"REQ-{datetime.now(UTC).year}{count + 1:04d}"


def _generate_slug(title: str) -> str:
    return f"{slugify(title)}-{secrets.token_hex(3)}"


def create_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    notes: list[dict] | None = None,
    custom_fields: list[dict] | None = None,
    search_criteria: dict | None = None,
    **fields,
) -> Job:
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
    db.flush()

    for note in notes or []:
        db.add(JobNote(job_id=job.id, author_id=actor_id, **note))
    for custom_field in custom_fields or []:
        db.add(JobCustomField(job_id=job.id, **custom_field))
    if search_criteria:
        db.add(JobSearchCriteria(job_id=job.id, **search_criteria))

    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID, *, viewer: CurrentUser | None = None) -> Job:
    query = select(Job).where(Job.id == job_id, Job.organization_id == organization_id, Job.deleted_at.is_(None))
    job = db.scalar(_scope_filter(query, viewer))
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
    viewer: CurrentUser | None = None,
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
    query = _scope_filter(query, viewer)
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
        job.posted_at = datetime.now(UTC)
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
    hires_count = (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.job_id == job_id, Application.status == ApplicationStatus.HIRED.value
            )
        )
        or 0
    )
    shortlisted_count = (
        db.scalar(
            select(func.count(Application.id))
            .join(StageTemplateStage, Application.current_stage_id == StageTemplateStage.id)
            .where(Application.job_id == job_id, StageTemplateStage.name == "Shortlisted")
        )
        or 0
    )
    return {
        "applications_count": applications_count,
        "shortlisted_count": shortlisted_count,
        "interviews_count": 0,
        "offers_count": 0,
        "hires_count": hires_count,
    }


# --- Job snapshot sections -------------------------------------------------


def upsert_search_criteria(db: Session, job: Job, **fields) -> JobSearchCriteria:
    criteria = db.scalar(select(JobSearchCriteria).where(JobSearchCriteria.job_id == job.id))
    if criteria is None:
        criteria = JobSearchCriteria(job_id=job.id, **fields)
        db.add(criteria)
    else:
        for key, value in fields.items():
            setattr(criteria, key, value)
    db.commit()
    db.refresh(criteria)
    return criteria


def set_custom_field(db: Session, job: Job, *, field_name: str, field_value: str | None) -> JobCustomField:
    field = db.scalar(select(JobCustomField).where(JobCustomField.job_id == job.id, JobCustomField.field_name == field_name))
    if field is None:
        field = JobCustomField(job_id=job.id, field_name=field_name, field_value=field_value)
        db.add(field)
    else:
        field.field_value = field_value
    db.commit()
    db.refresh(field)
    return field


def add_note(db: Session, job: Job, *, author_id: uuid.UUID | None, **fields) -> JobNote:
    note = JobNote(job_id=job.id, author_id=author_id, **fields)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, job: Job) -> list[JobNote]:
    return list(
        db.scalars(
            select(JobNote)
            .where(JobNote.job_id == job.id)
            .options(selectinload(JobNote.author))
            .order_by(JobNote.created_at.desc())
        ).all()
    )


def add_document(
    db: Session,
    job: Job,
    *,
    file_name: str,
    content_type: str,
    data: bytes,
    uploaded_by: uuid.UUID | None,
) -> JobDocument:
    key = f"jobs/{job.id}/{uuid.uuid4()}-{file_name}"
    storage_service.upload_bytes(key, data, content_type)
    document = JobDocument(
        job_id=job.id,
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(data),
        storage_key=key,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, job: Job, document_id: uuid.UUID) -> JobDocument:
    """Fetch one document, scoped to the job it belongs to, so a document id
    cannot be used to reach a file hanging off a record the caller cannot see."""
    document = db.scalar(
        select(JobDocument).where(
            JobDocument.id == document_id,
            JobDocument.job_id == job.id,
        )
    )
    if document is None:
        raise NotFoundError("Document not found")
    return document


def list_documents(db: Session, job: Job) -> list[JobDocument]:
    return list(
        db.scalars(select(JobDocument).where(JobDocument.job_id == job.id).order_by(JobDocument.created_at.desc())).all()
    )


def job_age_days(job: Job) -> int:
    return max((datetime.now(UTC) - job.created_at).days, 0)


def list_submissions(db: Session, job: Job) -> dict:
    """Submissions grid for the job snapshot: one row per application, with the
    candidate's position along this job's stage template."""
    stages = list(
        db.scalars(
            select(StageTemplateStage)
            .where(StageTemplateStage.template_id == job.stage_template_id)
            .order_by(StageTemplateStage.sort_order)
        ).all()
    )
    stage_order = {s.id: i for i, s in enumerate(stages)}

    applications = list(
        db.scalars(
            select(Application)
            .where(Application.job_id == job.id)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.current_stage),
                selectinload(Application.stage_history),
            )
            .order_by(Application.applied_at.desc())
        ).all()
    )

    actor_ids = {h.changed_by for a in applications for h in a.stage_history if h.changed_by}
    actor_names = (
        {row[0]: row[1] for row in db.execute(select(User.id, User.full_name).where(User.id.in_(actor_ids))).all()}
        if actor_ids
        else {}
    )

    rows = []
    for application in applications:
        first_move = application.stage_history[0] if application.stage_history else None
        candidate = application.candidate
        rows.append(
            {
                "application_id": application.id,
                "candidate_id": application.candidate_id,
                "candidate_name": candidate.full_name if candidate else "—",
                "candidate_email": candidate.email if candidate else None,
                "candidate_phone": candidate.phone if candidate else None,
                "candidate_location": candidate.location if candidate else None,
                "work_auth": candidate.work_auth if candidate else None,
                "pay_expectation": candidate.expected_ctc if candidate else None,
                "source": application.source,
                "status": application.status,
                "current_stage_id": application.current_stage_id,
                "current_stage_name": application.current_stage.name if application.current_stage else None,
                "stage_index": stage_order.get(application.current_stage_id, 0),
                "applied_at": application.applied_at,
                "submitted_by": first_move.changed_by if first_move else None,
                "submitted_by_name": actor_names.get(first_move.changed_by) if first_move else None,
                "submitted_at": first_move.created_at if first_move else application.applied_at,
            }
        )

    counts = {stage.name: 0 for stage in stages}
    for row in rows:
        if row["current_stage_name"] in counts:
            counts[row["current_stage_name"]] += 1
    counts["All"] = len(rows)

    return {"stages": [s.name for s in stages], "submissions": rows, "counts": counts}
