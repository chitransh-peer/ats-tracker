import re
import uuid
from dataclasses import dataclass, field

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CandidateDocumentType, JobStatus
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.candidate import Candidate, CandidateEducation
from app.db.models.job import Job
from app.services.ai.evaluation import create_pending_evaluation
from app.services.ai.resume_parsing import create_pending_run
from app.services.applications.service import create_application
from app.services.candidates.service import add_document
from app.services.careers.questions import role_questions, wants_portfolio_links, wants_sponsorship_question


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


@dataclass
class ApplicantProfile:
    location: str
    current_title: str
    total_experience_years: float
    highest_qualification: str
    notice_period: str
    expected_ctc: str
    work_arrangement_ok: str
    current_company: str | None = None
    relevant_experience_years: float | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None
    college: str | None = None
    graduation_year: str | None = None
    earliest_joining_date: str | None = None
    current_ctc: str | None = None
    heard_from: str | None = None
    work_authorized: str | None = None
    needs_sponsorship: str | None = None
    role_answers: dict[str, str] = field(default_factory=dict)


def _clean(value: str | float | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clip(value: str | None, length: int) -> str | None:
    text = _clean(value)
    return text[:length] if text else None


def _ctc_number(value: str | None) -> int | None:
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits and len(digits) <= 9 else None


def _build_answers(job: Job, profile: ApplicantProfile) -> list[dict]:
    """The form as the candidate saw it, section by section, blanks left out.
    Raises ValidationAppError when a required role-specific answer is missing."""
    rows: list[tuple[str, str, str | float | None]] = [
        ("Personal Details", "Current City / Location", profile.location),
        ("Professional Profile", "Current Job Title", profile.current_title),
        ("Professional Profile", "Current Company", profile.current_company),
        ("Professional Profile", "Total Years of Experience", profile.total_experience_years),
        ("Professional Profile", "Relevant Years of Experience", profile.relevant_experience_years),
        ("Resume & Portfolio", "LinkedIn Profile", profile.linkedin_url),
        ("Resume & Portfolio", "Portfolio / Personal Website", profile.portfolio_url),
    ]
    if wants_portfolio_links(job):
        rows.append(("Resume & Portfolio", "GitHub / Behance / Dribbble", profile.github_url))
    rows += [
        ("Education", "Highest Qualification", profile.highest_qualification),
        ("Education", "College / University", profile.college),
        ("Education", "Graduation Year", profile.graduation_year),
    ]
    for question in role_questions(job):
        answer = _clean(profile.role_answers.get(question["key"]))
        if question["required"] and not answer:
            raise ValidationAppError(f"Please answer: {question['label']}")
        rows.append(("Role-Specific Questions", question["label"], answer))
    rows += [
        ("Availability & Compensation", "Notice Period", profile.notice_period),
        ("Availability & Compensation", "Earliest Joining Date", profile.earliest_joining_date),
        ("Availability & Compensation", "Current CTC", profile.current_ctc),
        ("Availability & Compensation", "Expected CTC", profile.expected_ctc),
        ("Availability & Compensation", "Open to the work arrangement in the JD", profile.work_arrangement_ok),
        ("Additional Questions", "How did you hear about this opportunity?", profile.heard_from),
        ("Additional Questions", "Authorized to work in the required location/country?", profile.work_authorized),
    ]
    if wants_sponsorship_question(job):
        rows.append(("Additional Questions", "Requires sponsorship?", profile.needs_sponsorship))
    answers = []
    for section, question, value in rows:
        answer = _clean(value)
        if answer is not None:
            answers.append({"section": section, "question": question, "answer": answer[:5000]})
    return answers


def _fill_new_candidate(candidate: Candidate, profile: ApplicantProfile) -> None:
    candidate.location = _clip(profile.location, 255)
    candidate.current_title = _clip(profile.current_title, 255)
    candidate.current_company = _clip(profile.current_company, 255)
    candidate.total_experience_years = profile.total_experience_years
    candidate.relevant_experience_years = profile.relevant_experience_years
    candidate.linkedin_url = _clip(profile.linkedin_url, 500)
    candidate.notice_period = _clip(profile.notice_period, 50)
    candidate.current_ctc = _ctc_number(profile.current_ctc)
    candidate.expected_ctc = _ctc_number(profile.expected_ctc)
    candidate.work_auth = _clip(profile.work_authorized, 100)
    if _clean(profile.highest_qualification):
        candidate.education.append(
            CandidateEducation(
                degree=_clip(profile.highest_qualification, 255),
                school=_clip(profile.college, 255) or "Not given",
                year=_clip(profile.graduation_year, 10),
            )
        )


def apply_to_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    full_name: str,
    email: str,
    phone: str | None,
    profile: ApplicantProfile | None = None,
    resume_bytes: bytes | None,
    resume_file_name: str | None,
    resume_content_type: str | None,
    background_tasks: BackgroundTasks,
):
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value)
    )
    if job is None:
        raise NotFoundError("Job not found")
    answers = _build_answers(job, profile) if profile is not None else []

    candidate = db.scalar(select(Candidate).where(Candidate.organization_id == organization_id, Candidate.email == email))
    # Nothing proves the person filling in this public form owns the email they
    # typed. For a new candidate that does not matter; for an existing one it
    # would let anyone replace a real candidate's résumé, and through parsing
    # their profile, just by knowing their address.
    existing_candidate = candidate is not None
    if candidate is None:
        candidate = Candidate(
            organization_id=organization_id, full_name=full_name, email=email, phone=phone, source="Careers Page"
        )
        # Only a new record takes the form's profile fields; an existing one is
        # not overwritten by an unverified submission (see above). Its answers
        # still land on the application.
        if profile is not None:
            _fill_new_candidate(candidate, profile)
        db.add(candidate)
        db.flush()

    application = create_application(
        db, organization_id=organization_id, candidate_id=candidate.id, job_id=job.id, source="Careers Page"
    )
    application.answers = answers

    document = None
    if resume_bytes and resume_file_name and resume_content_type:
        if existing_candidate:
            # Kept for a recruiter to look at, but not as their résumé and not
            # parsed into their record: the upload is unverified.
            add_document(
                db,
                candidate,
                document_type=CandidateDocumentType.OTHER.value,
                file_name=f"Unverified careers-page upload - {resume_file_name}",
                content_type=resume_content_type,
                data=resume_bytes,
                uploaded_by=None,
            )
        else:
            document = add_document(
                db,
                candidate,
                document_type=CandidateDocumentType.RESUME.value,
                file_name=resume_file_name,
                content_type=resume_content_type,
                data=resume_bytes,
                uploaded_by=None,
            )

    # Kick off AI review automatically so every careers-page applicant gets a score.
    # Imported here to avoid a service<->worker import cycle at module load.
    #
    # After the response, not inline: a candidate submitting an application
    # should get their confirmation at once, not wait half a minute on an LLM.
    # With a worker deployed this is queued; without one it runs in this process
    # once the response is out. Either way it happens -- the old behaviour on a
    # deployment with no worker was to skip it and leave the applicant unscored.
    from app.services.ai.recovery import resume_stalled_work
    from app.workers.dispatch import dispatch_after_response
    from app.workers.tasks.ai import evaluate_application_task, parse_resume_task

    evaluation = create_pending_evaluation(db, organization_id=organization_id, application_id=application.id, actor_id=None)
    if document is not None:
        run = create_pending_run(db, organization_id=organization_id, candidate_id=candidate.id, document_id=document.id)
        # Parse first, then chain evaluation once the résumé text is available.
        dispatch_after_response(background_tasks, parse_resume_task, str(run.id), str(evaluation.id))
    else:
        dispatch_after_response(background_tasks, evaluate_application_task, str(evaluation.id))
    # And pick up any earlier applicant whose scoring was cut short.
    background_tasks.add_task(resume_stalled_work)

    return application, candidate
