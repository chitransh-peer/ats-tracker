import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CandidateDocumentType, JobStatus
from app.core.exceptions import NotFoundError
from app.db.models.candidate import Candidate
from app.db.models.job import Job
from app.services.applications.service import create_application
from app.services.candidates.service import add_document


def list_published_jobs(db: Session, organization_id: uuid.UUID) -> list[Job]:
    return list(
        db.scalars(
            select(Job)
            .where(
                Job.organization_id == organization_id,
                Job.status == JobStatus.ACTIVE.value,
                Job.deleted_at.is_(None),
            )
            .order_by(Job.posted_at.desc())
        ).all()
    )


def get_published_job_by_slug(db: Session, organization_id: uuid.UUID, slug: str) -> Job:
    job = db.scalar(
        select(Job).where(
            Job.organization_id == organization_id,
            Job.slug == slug,
            Job.status == JobStatus.ACTIVE.value,
            Job.deleted_at.is_(None),
        )
    )
    if job is None:
        raise NotFoundError("Job not found")
    return job


def apply_to_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    full_name: str,
    email: str,
    phone: str | None,
    resume_bytes: bytes | None,
    resume_file_name: str | None,
    resume_content_type: str | None,
):
    job = db.scalar(
        select(Job).where(
            Job.id == job_id, Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value
        )
    )
    if job is None:
        raise NotFoundError("Job not found")

    candidate = db.scalar(
        select(Candidate).where(Candidate.organization_id == organization_id, Candidate.email == email)
    )
    if candidate is None:
        candidate = Candidate(organization_id=organization_id, full_name=full_name, email=email, phone=phone, source="Careers Page")
        db.add(candidate)
        db.flush()

    application = create_application(
        db, organization_id=organization_id, candidate_id=candidate.id, job_id=job.id, source="Careers Page"
    )

    if resume_bytes and resume_file_name and resume_content_type:
        add_document(
            db,
            candidate,
            document_type=CandidateDocumentType.RESUME.value,
            file_name=resume_file_name,
            content_type=resume_content_type,
            data=resume_bytes,
            uploaded_by=None,
        )

    return application, candidate
