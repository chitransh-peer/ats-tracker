import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundError
from app.db.models.organization import Organization
from app.schemas.careers import PublicApplyResponse, PublicJobRead
from app.services.careers import service as careers_service

router = APIRouter(prefix="/careers", tags=["careers"])


def _get_public_organization(db: Session, org_slug: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == org_slug))
    if org is None or org.settings is None or not org.settings.careers_page_enabled:
        raise NotFoundError("Careers page not found")
    return org


@router.get("/{org_slug}/jobs", response_model=list[PublicJobRead])
def list_jobs(org_slug: str, db: Session = Depends(get_db_session)) -> list[PublicJobRead]:
    org = _get_public_organization(db, org_slug)
    return careers_service.list_published_jobs(db, org.id)


@router.get("/{org_slug}/jobs/{slug}", response_model=PublicJobRead)
def get_job(org_slug: str, slug: str, db: Session = Depends(get_db_session)) -> PublicJobRead:
    org = _get_public_organization(db, org_slug)
    return careers_service.get_published_job_by_slug(db, org.id, slug)


@router.post("/{org_slug}/jobs/{job_id}/apply", response_model=PublicApplyResponse, status_code=201)
async def apply_to_job(
    org_slug: str,
    job_id: uuid.UUID,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(None),
    resume: UploadFile | None = File(None),
    db: Session = Depends(get_db_session),
) -> PublicApplyResponse:
    org = _get_public_organization(db, org_slug)

    resume_bytes = await resume.read() if resume else None
    application, candidate = careers_service.apply_to_job(
        db,
        organization_id=org.id,
        job_id=job_id,
        full_name=full_name,
        email=email,
        phone=phone,
        resume_bytes=resume_bytes,
        resume_file_name=resume.filename if resume else None,
        resume_content_type=resume.content_type if resume else None,
    )
    return PublicApplyResponse(application_id=application.id, candidate_id=candidate.id, status=application.status)
