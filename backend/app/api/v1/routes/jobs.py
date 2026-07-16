import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.application import ApplicationRead
from app.schemas.auth import CurrentUser
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.services.applications.service import list_applications
from app.services.audit.service import record as record_audit
from app.services.jobs import service as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_read(db: Session, job) -> JobRead:
    stats = job_service.job_stats(db, job.id)
    return JobRead(
        id=job.id,
        organization_id=job.organization_id,
        req_id=job.req_id,
        slug=job.slug,
        title=job.title,
        department=job.department,
        client_id=job.client_id,
        hiring_manager_id=job.hiring_manager_id,
        recruiter_id=job.recruiter_id,
        stage_template_id=job.stage_template_id,
        location=job.location,
        workplace=job.workplace,
        employment_type=job.employment_type,
        openings=job.openings,
        pay_min=job.pay_min,
        pay_max=job.pay_max,
        priority=job.priority,
        status=job.status,
        summary=job.summary,
        description=job.description,
        responsibilities=job.responsibilities,
        required_skills=job.required_skills,
        nice_to_have=job.nice_to_have,
        screening_questions=job.screening_questions,
        experience=job.experience,
        education=job.education,
        posted_at=job.posted_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        **stats,
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
        db, current_user.organization_id, status=status, department=department, client_id=client_id, recruiter_id=recruiter_id
    )
    return [_to_read(db, j) for j in jobs]


@router.post("", response_model=JobRead, status_code=201)
def create_job(
    payload: JobCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> JobRead:
    job = job_service.create_job(
        db, organization_id=current_user.organization_id, actor_id=current_user.id, **payload.model_dump()
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
    job = job_service.get_job(db, current_user.organization_id, job_id)
    return _to_read(db, job)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.JOB, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> JobRead:
    job = job_service.get_job(db, current_user.organization_id, job_id)
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
        job = job_service.get_job(db, current_user.organization_id, job_id)
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
    job_service.get_job(db, current_user.organization_id, job_id)
    return list_applications(db, current_user.organization_id, job_id=job_id)
