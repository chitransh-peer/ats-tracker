import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.file_validation import validate_resume_upload
from app.core.rate_limit import limiter
from app.db.models.organization import Organization
from app.schemas.careers import PublicApplyResponse, PublicJobRead, PublicOrganizationRead
from app.services.careers import questions as careers_questions
from app.services.careers import service as careers_service

router = APIRouter(prefix="/careers", tags=["careers"])


def _get_public_organization(db: Session, org_slug: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == org_slug))
    if org is None or org.settings is None or not org.settings.careers_page_enabled:
        raise NotFoundError("Careers page not found")
    return org


def _public_job(job) -> PublicJobRead:
    read = PublicJobRead.model_validate(job)
    read.role_questions = careers_questions.role_questions(job)
    read.ask_portfolio_links = careers_questions.wants_portfolio_links(job)
    read.ask_sponsorship = careers_questions.wants_sponsorship_question(job)
    return read


@router.get("/{org_slug}", response_model=PublicOrganizationRead)
def get_organization(org_slug: str, db: Session = Depends(get_db_session)) -> PublicOrganizationRead:
    org = _get_public_organization(db, org_slug)
    return PublicOrganizationRead(name=org.name, slug=org.slug)


@router.get("/{org_slug}/jobs", response_model=list[PublicJobRead])
def list_jobs(org_slug: str, db: Session = Depends(get_db_session)) -> list[PublicJobRead]:
    org = _get_public_organization(db, org_slug)
    return [_public_job(job) for job in careers_service.list_published_jobs(db, org.id)]


@router.get("/{org_slug}/jobs/{slug}", response_model=PublicJobRead)
def get_job(org_slug: str, slug: str, db: Session = Depends(get_db_session)) -> PublicJobRead:
    org = _get_public_organization(db, org_slug)
    return _public_job(careers_service.get_published_job_by_slug(db, org.id, slug))


@router.post("/{org_slug}/jobs/{job_id}/apply", response_model=PublicApplyResponse, status_code=201)
@limiter.limit("20/minute")
async def apply_to_job(
    request: Request,
    background_tasks: BackgroundTasks,
    org_slug: str,
    job_id: uuid.UUID,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(..., min_length=5, max_length=50),
    location: str = Form(..., min_length=1, max_length=255),
    current_title: str = Form(..., min_length=1, max_length=255),
    current_company: str | None = Form(None, max_length=255),
    total_experience_years: float = Form(..., ge=0, le=60),
    relevant_experience_years: float | None = Form(None, ge=0, le=60),
    linkedin_url: str | None = Form(None, max_length=500),
    portfolio_url: str | None = Form(None, max_length=500),
    github_url: str | None = Form(None, max_length=500),
    highest_qualification: str = Form(..., min_length=1, max_length=255),
    college: str | None = Form(None, max_length=255),
    graduation_year: str | None = Form(None, max_length=10),
    notice_period: str = Form(..., min_length=1, max_length=50),
    earliest_joining_date: str | None = Form(None, max_length=50),
    current_ctc: str | None = Form(None, max_length=50),
    expected_ctc: str = Form(..., min_length=1, max_length=50),
    work_arrangement_ok: str = Form(..., pattern="^(Yes|No)$"),
    heard_from: str | None = Form(None, max_length=255),
    work_authorized: str | None = Form(None, max_length=100),
    needs_sponsorship: str | None = Form(None, max_length=20),
    # JSON object of {question key: answer} for the role-specific section.
    role_answers: str | None = Form(None, max_length=50_000),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> PublicApplyResponse:
    org = _get_public_organization(db, org_slug)

    try:
        parsed_role_answers = json.loads(role_answers) if role_answers else {}
        if not isinstance(parsed_role_answers, dict):
            raise ValueError
    except ValueError as exc:
        raise ValidationAppError("Role-specific answers are malformed") from exc
    profile = careers_service.ApplicantProfile(
        location=location,
        current_title=current_title,
        current_company=current_company,
        total_experience_years=total_experience_years,
        relevant_experience_years=relevant_experience_years,
        linkedin_url=linkedin_url,
        portfolio_url=portfolio_url,
        github_url=github_url,
        highest_qualification=highest_qualification,
        college=college,
        graduation_year=graduation_year,
        notice_period=notice_period,
        earliest_joining_date=earliest_joining_date,
        current_ctc=current_ctc,
        expected_ctc=expected_ctc,
        work_arrangement_ok=work_arrangement_ok,
        heard_from=heard_from,
        work_authorized=work_authorized,
        needs_sponsorship=needs_sponsorship,
        role_answers={str(k): str(v) for k, v in parsed_role_answers.items()},
    )

    resume_bytes = await resume.read()
    # This is the one upload path on the whole API with no logged-in user
    # behind it, so it gets the strictest check: format-restricted, with a
    # magic-byte check against the declared extension.
    validate_resume_upload(data=resume_bytes, file_name=resume.filename or "resume")

    application, candidate = careers_service.apply_to_job(
        db,
        organization_id=org.id,
        job_id=job_id,
        full_name=full_name,
        email=email,
        phone=phone,
        profile=profile,
        resume_bytes=resume_bytes,
        resume_file_name=resume.filename or "resume",
        resume_content_type=resume.content_type or "application/octet-stream",
        background_tasks=background_tasks,
    )
    return PublicApplyResponse(application_id=application.id, candidate_id=candidate.id, status=application.status)
