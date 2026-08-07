import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.application import ApplicationRead
from app.schemas.auth import CurrentUser
from app.schemas.job import (
    JobCreate,
    JobCustomFieldCreate,
    JobCustomFieldRead,
    JobDocumentRead,
    JobNoteCreate,
    JobNoteRead,
    JobRead,
    JobSearchCriteriaRead,
    JobSearchCriteriaWrite,
    JobSubmissionsSummary,
    JobUpdate,
)
from app.services.applications.service import list_applications
from app.services.audit.service import record as record_audit
from app.services.jobs import service as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


_SKIP_COLUMNS = {"created_by", "updated_by", "deleted_at"}


def _to_read(db: Session, job) -> JobRead:
    stats = job_service.job_stats(db, job.id)
    assigned_names = job_service_user_names(db, job.assigned_to_ids)
    return JobRead(
        **{
            column.name: getattr(job, column.name)
            for column in job.__table__.columns
            if column.name not in _SKIP_COLUMNS
        },
        created_by=job.created_by,
        updated_by=job.updated_by,
        client_name=job.client.name if job.client else None,
        sales_manager_name=job.sales_manager.full_name if job.sales_manager else None,
        recruitment_manager_name=(
            job.recruitment_manager.full_name if job.recruitment_manager else None
        ),
        account_manager_name=job.account_manager.full_name if job.account_manager else None,
        primary_recruiter_name=job.primary_recruiter.full_name if job.primary_recruiter else None,
        assigned_to_names=[assigned_names[uid] for uid in job.assigned_to_ids if uid in assigned_names],
        created_by_name=job.created_by_user.full_name if job.created_by_user else None,
        updated_by_name=job.updated_by_user.full_name if job.updated_by_user else None,
        job_age_days=job_service.job_age_days(job),
        custom_fields=job.custom_fields,
        search_criteria=job.search_criteria,
        **stats,
    )


def job_service_user_names(db: Session, user_ids) -> dict:
    from app.db.models.user import User

    if not user_ids:
        return {}
    rows = db.execute(select(User.id, User.full_name).where(User.id.in_(set(user_ids)))).all()
    return {row[0]: row[1] for row in rows}


def _note_read(note) -> JobNoteRead:
    return JobNoteRead(
        id=note.id,
        body=note.body,
        note_type=note.note_type,
        action=note.action,
        author_id=note.author_id,
        author_name=note.author.full_name if note.author else None,
        created_at=note.created_at,
    )


@router.get("", response_model=list[JobRead])
def list_jobs(
    status: str | None = None,
    department: str | None = None,
    client_id: uuid.UUID | None = None,
    recruiter_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[JobRead]:
    jobs = job_service.list_jobs(
        db,
        current_user.organization_id,
        status=status,
        department=department,
        client_id=client_id,
        recruiter_id=recruiter_id,
        viewer=current_user,
    )
    return [_to_read(db, j) for j in jobs]


@router.post("", response_model=JobRead, status_code=201)
def create_job(
    payload: JobCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> JobRead:
    data = payload.model_dump()
    job = job_service.create_job(
        db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        notes=data.pop("notes", []),
        custom_fields=data.pop("custom_fields", []),
        search_criteria=data.pop("search_criteria", None),
        **data,
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.JOB_CREATED.value,
        resource_type="job",
        resource_id=str(job.id),
    )
    db.commit()
    return _to_read(db, job)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> JobRead:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return _to_read(db, job)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> JobRead:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    job = job_service.update_job(db, job, actor_id=current_user.id, **payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.JOB_UPDATED.value,
        resource_type="job",
        resource_id=str(job.id),
    )
    db.commit()
    return _to_read(db, job)


def _transition_route(transition_fn, audit_action: AuditAction):
    def _handler(
        job_id: uuid.UUID,
        current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.UPDATE)),
        db: Session = Depends(get_db_session),
    ) -> JobRead:
        job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
        job = transition_fn(db, job, actor_id=current_user.id)
        record_audit(
            db,
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
            action=audit_action.value,
            resource_type="job",
            resource_id=str(job.id),
        )
        db.commit()
        return _to_read(db, job)

    return _handler


router.add_api_route(
    "/{job_id}/publish", _transition_route(job_service.publish_job, AuditAction.JOB_PUBLISHED), methods=["POST"], response_model=JobRead
)
router.add_api_route(
    "/{job_id}/unpublish", _transition_route(job_service.unpublish_job, AuditAction.JOB_UNPUBLISHED), methods=["POST"], response_model=JobRead
)
router.add_api_route(
    "/{job_id}/close", _transition_route(job_service.close_job, AuditAction.JOB_CLOSED), methods=["POST"], response_model=JobRead
)
router.add_api_route(
    "/{job_id}/hold", _transition_route(job_service.hold_job, AuditAction.JOB_HELD), methods=["POST"], response_model=JobRead
)
router.add_api_route(
    "/{job_id}/cancel", _transition_route(job_service.cancel_job, AuditAction.JOB_CANCELLED), methods=["POST"], response_model=JobRead
)


@router.get("/{job_id}/applications", response_model=list[ApplicationRead])
def job_applications(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ApplicationRead]:
    job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return list_applications(db, current_user.organization_id, job_id=job_id, viewer=current_user)


# --- Job snapshot sections -------------------------------------------------

_JOB_READ = require_permission(PermissionResource.JOB, PermissionAction.READ)
_JOB_UPDATE = require_permission(PermissionResource.JOB, PermissionAction.UPDATE)


@router.get("/{job_id}/submissions", response_model=JobSubmissionsSummary)
def job_submissions(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(_JOB_READ),
    db: Session = Depends(get_db_session),
) -> JobSubmissionsSummary:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return JobSubmissionsSummary(**job_service.list_submissions(db, job))


@router.get("/{job_id}/notes", response_model=list[JobNoteRead])
def list_job_notes(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(_JOB_READ),
    db: Session = Depends(get_db_session),
) -> list[JobNoteRead]:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return [_note_read(n) for n in job_service.list_notes(db, job)]


@router.post("/{job_id}/notes", response_model=JobNoteRead, status_code=201)
def add_job_note(
    job_id: uuid.UUID,
    payload: JobNoteCreate,
    current_user: CurrentUser = Depends(_JOB_UPDATE),
    db: Session = Depends(get_db_session),
) -> JobNoteRead:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    note = job_service.add_note(db, job, author_id=current_user.id, **payload.model_dump())
    return _note_read(note)


@router.get("/{job_id}/documents", response_model=list[JobDocumentRead])
def list_job_documents(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(_JOB_READ),
    db: Session = Depends(get_db_session),
) -> list[JobDocumentRead]:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return job_service.list_documents(db, job)


@router.post("/{job_id}/documents", response_model=JobDocumentRead, status_code=201)
async def upload_job_document(
    job_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(_JOB_UPDATE),
    db: Session = Depends(get_db_session),
) -> JobDocumentRead:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    data = await file.read()
    return job_service.add_document(
        db,
        job,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        uploaded_by=current_user.id,
    )


@router.put("/{job_id}/search-criteria", response_model=JobSearchCriteriaRead)
def save_job_search_criteria(
    job_id: uuid.UUID,
    payload: JobSearchCriteriaWrite,
    current_user: CurrentUser = Depends(_JOB_UPDATE),
    db: Session = Depends(get_db_session),
) -> JobSearchCriteriaRead:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return job_service.upsert_search_criteria(db, job, **payload.model_dump())


@router.put("/{job_id}/custom-fields", response_model=JobCustomFieldRead)
def set_job_custom_field(
    job_id: uuid.UUID,
    payload: JobCustomFieldCreate,
    current_user: CurrentUser = Depends(_JOB_UPDATE),
    db: Session = Depends(get_db_session),
) -> JobCustomFieldRead:
    job = job_service.get_job(db, current_user.organization_id, job_id, viewer=current_user)
    return job_service.set_custom_field(
        db, job, field_name=payload.field_name, field_value=payload.field_value
    )
