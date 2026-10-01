import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, false, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ApplicationStatus, JobStatus, RoleName
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.client import Client
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
    if RoleName.CANDIDATE.value in scopes:
        # The self-service role sees what the public careers page shows, not
        # drafts, held or closed requisitions.
        conditions.append(Job.status == JobStatus.ACTIVE.value)
    # false() first: with no condition for this viewer's roles, nothing matches.
    return query.where(or_(false(), *conditions))


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


# Everything JobRead names, loaded for a whole page in a handful of queries
# instead of one lazy load per relationship per job.
_READ_LOAD_OPTIONS = (
    selectinload(Job.client),
    selectinload(Job.sales_manager),
    selectinload(Job.recruitment_manager),
    selectinload(Job.account_manager),
    selectinload(Job.primary_recruiter),
    selectinload(Job.created_by_user),
    selectinload(Job.updated_by_user),
    selectinload(Job.custom_fields),
    selectinload(Job.search_criteria),
)


def _search_filter(search: str | None):
    """Case-insensitive "contains" on title, job code and client name."""
    if not search or not search.strip():
        return None
    like = f"%{search.strip()}%"
    return or_(
        Job.title.ilike(like),
        Job.req_id.ilike(like),
        Job.client_id.in_(select(Client.id).where(Client.name.ilike(like))),
    )


def build_jobs_query(
    organization_id: uuid.UUID,
    *,
    status: str | None = None,
    department: str | None = None,
    client_id: uuid.UUID | None = None,
    recruiter_id: uuid.UUID | None = None,
    search: str | None = None,
    viewer: CurrentUser | None = None,
) -> Select:
    """Filtered, scoped, newest-first job query; the caller pages it
    (app/core/pagination.py)."""
    query = select(Job).where(Job.organization_id == organization_id, Job.deleted_at.is_(None))
    if status is not None:
        query = query.where(Job.status == status)
    if department is not None:
        query = query.where(Job.department == department)
    if client_id is not None:
        query = query.where(Job.client_id == client_id)
    if recruiter_id is not None:
        query = query.where(Job.recruiter_id == recruiter_id)
    condition = _search_filter(search)
    if condition is not None:
        query = query.where(condition)
    query = _scope_filter(query, viewer)
    return query.options(*_READ_LOAD_OPTIONS).order_by(Job.created_at.desc(), Job.id)


def job_summary(db: Session, organization_id: uuid.UUID, *, viewer: CurrentUser | None = None) -> dict[str, int]:
    """The list page's headline counts, counted by the database within the
    viewer's scope, rather than by loading every job into the browser."""
    rows = db.execute(
        _scope_filter(
            select(Job.status, func.count(Job.id))
            .where(Job.organization_id == organization_id, Job.deleted_at.is_(None))
            .group_by(Job.status),
            viewer,
        )
    ).all()
    by_status = dict(rows)
    return {
        "total": sum(by_status.values()),
        "active": by_status.get(JobStatus.ACTIVE.value, 0),
        "draft": by_status.get(JobStatus.DRAFT.value, 0),
        "closed_or_on_hold": by_status.get(JobStatus.CLOSED.value, 0) + by_status.get(JobStatus.ON_HOLD.value, 0),
    }


def job_options(
    db: Session,
    organization_id: uuid.UUID,
    *,
    search: str | None = None,
    ids: list[uuid.UUID] | None = None,
    status: str | None = None,
    limit: int = 20,
    viewer: CurrentUser | None = None,
) -> list[tuple[uuid.UUID, str, str, str]]:
    """(id, title, req_id, status) for a type-to-search picker: the first
    `limit` matches, or the named `ids` so a picker can label its value."""
    query = select(Job.id, Job.title, Job.req_id, Job.status).where(
        Job.organization_id == organization_id, Job.deleted_at.is_(None)
    )
    if ids:
        query = query.where(Job.id.in_(ids))
    else:
        condition = _search_filter(search)
        if condition is not None:
            query = query.where(condition)
        if status:
            query = query.where(Job.status == status)
    query = _scope_filter(query, viewer).order_by(Job.created_at.desc(), Job.id).limit(limit)
    return [(row.id, row.title, row.req_id, row.status) for row in db.execute(query).all()]


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


def job_stats_empty() -> dict[str, int]:
    return {
        "applications_count": 0,
        "shortlisted_count": 0,
        "interviews_count": 0,
        "offers_count": 0,
        "hires_count": 0,
    }


def jobs_stats(db: Session, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    """Application, shortlist and hire counts for a whole page of jobs in one
    grouped query. A job with no applications is absent from the result."""
    if not job_ids:
        return {}
    rows = db.execute(
        select(
            Application.job_id,
            func.count(Application.id),
            func.count(Application.id).filter(StageTemplateStage.name == "Shortlisted"),
            func.count(Application.id).filter(Application.status == ApplicationStatus.HIRED.value),
        )
        .outerjoin(StageTemplateStage, Application.current_stage_id == StageTemplateStage.id)
        .where(Application.job_id.in_(job_ids))
        .group_by(Application.job_id)
    ).all()
    return {
        job_id: {**job_stats_empty(), "applications_count": total, "shortlisted_count": shortlisted, "hires_count": hires}
        for job_id, total, shortlisted, hires in rows
    }


def job_stats(db: Session, job_id: uuid.UUID) -> dict[str, int]:
    return jobs_stats(db, [job_id]).get(job_id, job_stats_empty())


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
