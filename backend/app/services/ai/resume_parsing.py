import io
import uuid
from datetime import datetime, timezone

import docx
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.enums import ResumeParseStatus
from app.core.exceptions import NotFoundError
from app.db.models.ai import ParsedResume, ResumeParseRun
from app.db.models.candidate import CandidateDocument
from app.services.ai.provider import AIProviderError, current_model_name, generate_structured
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


def extract_text(content_type: str, data: bytes) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        document = docx.Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return data.decode("utf-8", errors="ignore")


def create_pending_run(
    db: Session, *, organization_id: uuid.UUID, candidate_id: uuid.UUID, document_id: uuid.UUID
) -> ResumeParseRun:
    document = db.get(CandidateDocument, document_id)
    if document is None or document.candidate_id != candidate_id:
        raise NotFoundError("Candidate document not found")

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
    if document is None:
        run.status = ResumeParseStatus.FAILED.value
        run.error_message = "Candidate document was deleted before parsing could run"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run

    raw_bytes = download_bytes(document.storage_key)
    raw_text = extract_text(document.content_type, raw_bytes)

    try:
        fields = generate_structured(_RESUME_EXTRACTION_PROMPT.format(resume_text=raw_text[:12000]))
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

    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def get_parse_run(db: Session, organization_id: uuid.UUID, run_id: uuid.UUID) -> ResumeParseRun:
    run = db.get(ResumeParseRun, run_id)
    if run is None or run.organization_id != organization_id:
        raise NotFoundError("Resume parse run not found")
    return run
