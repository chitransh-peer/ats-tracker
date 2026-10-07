import io
import uuid
from datetime import UTC, datetime

import docx
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.enums import ResumeParseStatus
from app.core.exceptions import NotFoundError
from app.db.models.ai import ParsedResume, ResumeParseRun
from app.db.models.candidate import Candidate, CandidateDocument
from app.services.ai.provider import AIProviderError, current_model_name, generate_structured
from app.services.ceipal.rules import NOT_SCORED_MESSAGE, ensure_ai_allowed, is_ceipal
from app.services.storage.service import download_bytes

_RESUME_EXTRACTION_PROMPT = """You are a resume parser. Extract structured fields from the \
resume text below and respond with ONLY a JSON object (no prose, no markdown fences) with \
these exact keys: full_name (string or null), email (string or null), phone (string or null), \
location (string or null), total_experience_years (number or null), skills (array of strings), \
education (array of objects with degree/school/year), work_history (array of objects with \
title/company/start_date/end_date/summary).

Resume text:
---
{resume_text}
---
"""


# No résumé needs more than this, so there is no reason to read a 300-page
# upload to the end. Both limits bound the work a hostile file can make the
# parser do. The text kept feeds skill matching; the first _PROMPT_CHARS of it
# go to the model.
_MAX_TEXT_CHARS = 50_000
_MAX_PDF_PAGES = 30
_PROMPT_CHARS = 12_000


class UnreadableResumeError(Exception):
    """The file could not be read as the format it claims to be."""


def extract_text(content_type: str, data: bytes) -> str:
    try:
        if content_type == "application/pdf":
            return _pdf_text(data)
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            document = docx.Document(io.BytesIO(data))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)[:_MAX_TEXT_CHARS]
    except Exception as exc:
        # A malformed or truncated file raises from deep inside the library.
        # That is a property of the upload, not a fault here, so it becomes a
        # failed parse with a reason rather than an unhandled error.
        raise UnreadableResumeError(f"The file could not be read ({type(exc).__name__}).") from exc
    if content_type == "application/msword":
        # python-docx reads only the .docx format; a legacy .doc is binary.
        raise UnreadableResumeError("Legacy .doc files cannot be read; save the résumé as PDF or .docx.")
    return data.decode("utf-8", errors="ignore")[:_MAX_TEXT_CHARS]


def _pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    length = 0
    for page in reader.pages[:_MAX_PDF_PAGES]:
        text = page.extract_text() or ""
        parts.append(text)
        length += len(text)
        if length >= _MAX_TEXT_CHARS:
            break
    return "\n".join(parts)[:_MAX_TEXT_CHARS]


def create_pending_run(
    db: Session, *, organization_id: uuid.UUID, candidate_id: uuid.UUID, document_id: uuid.UUID
) -> ResumeParseRun:
    document = db.get(CandidateDocument, document_id)
    if document is None or document.candidate_id != candidate_id:
        raise NotFoundError("Candidate document not found")
    ensure_ai_allowed(db.get(Candidate, candidate_id))

    run = ResumeParseRun(
        organization_id=organization_id,
        candidate_id=candidate_id,
        document_id=document_id,
        status=ResumeParseStatus.PENDING.value,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def parse_resume(db: Session, run: ResumeParseRun) -> ResumeParseRun:
    run.status = ResumeParseStatus.PROCESSING.value
    db.commit()

    document = db.get(CandidateDocument, run.document_id)
    if is_ceipal(db.get(Candidate, run.candidate_id)):
        run.status = ResumeParseStatus.FAILED.value
        run.error_message = NOT_SCORED_MESSAGE
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        return run
    if document is None:
        run.status = ResumeParseStatus.FAILED.value
        run.error_message = "Candidate document was deleted before parsing could run"
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        return run

    raw_bytes = download_bytes(document.storage_key)
    try:
        raw_text = extract_text(document.content_type, raw_bytes)
    except UnreadableResumeError as exc:
        run.status = ResumeParseStatus.FAILED.value
        run.error_message = str(exc)
        run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        return run

    try:
        fields = generate_structured(_RESUME_EXTRACTION_PROMPT.format(resume_text=raw_text[:_PROMPT_CHARS]))
        db.add(
            ParsedResume(
                resume_parse_run_id=run.id,
                candidate_id=run.candidate_id,
                full_name=fields.get("full_name"),
                email=fields.get("email"),
                phone=fields.get("phone"),
                location=fields.get("location"),
                total_experience_years=fields.get("total_experience_years"),
                skills=fields.get("skills") or [],
                education=fields.get("education") or [],
                work_history=fields.get("work_history") or [],
                raw_text=raw_text,
            )
        )
        run.status = ResumeParseStatus.COMPLETED.value
        run.model_name = current_model_name()

        # Backfill the candidate's structured fields from the résumé when they're
        # empty (e.g. careers-page applicants who only submitted a résumé), so the
        # candidate record and downstream skill matching aren't left blank.
        candidate = db.get(Candidate, run.candidate_id)
        if candidate is not None:
            parsed_skills = fields.get("skills") or []
            if not candidate.skills and parsed_skills:
                candidate.skills = parsed_skills
            if candidate.total_experience_years is None and fields.get("total_experience_years") is not None:
                candidate.total_experience_years = fields.get("total_experience_years")
            if not candidate.location and fields.get("location"):
                candidate.location = fields.get("location")
            if not candidate.current_title and fields.get("work_history"):
                first = fields["work_history"][0]
                if isinstance(first, dict) and first.get("title"):
                    candidate.current_title = first.get("title")
    except AIProviderError as exc:
        # Rule-based flows (skill matching) don't need parsed fields, so keep the
        # raw text available even when the AI extraction step itself failed.
        db.add(
            ParsedResume(
                resume_parse_run_id=run.id,
                candidate_id=run.candidate_id,
                raw_text=raw_text,
            )
        )
        run.status = ResumeParseStatus.FAILED.value
        run.error_message = str(exc)

    run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return run


def get_parse_run(db: Session, organization_id: uuid.UUID, run_id: uuid.UUID) -> ResumeParseRun:
    run = db.get(ResumeParseRun, run_id)
    if run is None or run.organization_id != organization_id:
        raise NotFoundError("Resume parse run not found")
    return run
