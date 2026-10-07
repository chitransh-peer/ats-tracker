"""Importing a Ceipal "applicants" backup -- candidates, their résumés and
the rest of what Ceipal holds on them.

    create_import          -> an empty import, status "staging"
    stage_rows (repeated)  -> table rows arrive in batches, from any number of parts
    process_next_chunk     -> candidates are created/updated a chunk at a time;
                              the first call checks what was staged and locks it
    attach_document (each) -> résumé files are matched by their stored name
                              and attached; any number of ZIP parts, any order,
                              and coming back later for the rest is fine
    finish                 -> "completed" (more documents can still be added)
    undo_import            -> walks it back, files included

Candidates imported here get `origin = "ceipal"`. They were vetted in Ceipal,
so nothing here or anywhere else sends them to AI: no résumé parsing, no
scoring (see app/services/ceipal/rules.py).
"""

import csv
import io
import re
import time
import unicodedata
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.enums import CandidateDocumentType, CandidateStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.file_validation import MAX_DOCUMENT_BYTES
from app.db.models.application import Application
from app.db.models.bench import BenchProfile
from app.db.models.candidate import Candidate, CandidateDocument, CandidateEducation, CandidateNote
from app.db.models.ceipal import CeipalImport, CeipalProfile, CeipalRow
from app.db.models.communication import OutboundMessage
from app.db.models.job import Job
from app.db.models.user import User
from app.services.ceipal.rules import CEIPAL_ORIGIN
from app.services.ceipal.tables import (
    APPLICANT_COLUMNS,
    TABLES_BY_KIND,
    USER_COLUMNS,
    clean_row,
    get,
    has_header,
)
from app.services.storage.service import build_storage_key, delete_object, upload_bytes

ORIGIN = CEIPAL_ORIGIN

# Import status
STAGING = "staging"
IMPORTING = "importing"
DOCUMENTS = "documents"
COMPLETED = "completed"
UNDOING = "undoing"
UNDONE = "undone"

# Staged row status
PENDING = "pending"
IMPORTED = "imported"
REJECTED = "rejected"
ATTACHED = "attached"
ORPHAN = "orphan"

CHUNK_SIZE = 200
MAX_ROWS_PER_BATCH = 5000

# What a document may be, by extension, and what it is served as. A file
# whose extension claims PDF/DOC/DOCX must also start like one.
_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".rtf": "application/rtf",
    ".txt": "text/plain",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".eml": "message/rfc822",
    ".msg": "application/vnd.ms-outlook",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".docx": (b"PK\x03\x04",),
    ".odt": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".msg": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
}
ALLOWED_DOCUMENT_EXTENSIONS = sorted(_CONTENT_TYPES)


# ------------------------------------------------------------------ helpers


def _now() -> datetime:
    return datetime.now(UTC)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _base_name(path: str) -> str:
    return _nfc(path.replace("\\", "/").rsplit("/", 1)[-1].strip())


def _extension(file_name: str) -> str:
    dot = file_name.rfind(".")
    return file_name[dot:].lower() if dot != -1 else ""


def _clip(value: str | None, length: int) -> str | None:
    if not value:
        return None
    return value[:length]


_EXPERIENCE = re.compile(r"(\d+(?:\.\d+)?)\s*(year|month)?", re.IGNORECASE)


def _experience_years(text: str) -> float | None:
    """ "9 Year(s)" -> 9.0, "6 Month(s)" -> 0.5."""
    match = _EXPERIENCE.search(text or "")
    if not match:
        return None
    value = float(match.group(1))
    if (match.group(2) or "").lower() == "month":
        value = round(value / 12, 1)
    return value if 0 <= value < 1000 else None


def _parse_datetime(text: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except (TypeError, ValueError):
            continue
    return None


_YEAR = re.compile(r"(19|20)\d{2}")


def _year(text: str) -> str | None:
    match = _YEAR.search(text or "")
    return match.group(0) if match else None


def _skills(*texts: str) -> list[str]:
    seen: dict[str, str] = {}
    for text in texts:
        for part in (text or "").split(","):
            skill = part.strip()[:100]
            if skill and skill.lower() not in seen:
                seen[skill.lower()] = skill
    return list(seen.values())[:200]


def _email(text: str) -> str | None:
    value = (text or "").strip().lower()
    return value[:255] if "@" in value and " " not in value else None


def get_import(db: Session, organization_id: uuid.UUID, import_id: uuid.UUID) -> CeipalImport:
    imp = db.get(CeipalImport, import_id)
    if imp is None or imp.organization_id != organization_id:
        raise NotFoundError("Import not found")
    return imp


def list_imports(db: Session, organization_id: uuid.UUID, limit: int = 20) -> list[CeipalImport]:
    return list(
        db.scalars(
            select(CeipalImport)
            .where(CeipalImport.organization_id == organization_id)
            .order_by(CeipalImport.created_at.desc())
            .limit(limit)
        ).all()
    )


# ------------------------------------------------------------------ staging


def create_import(db: Session, *, organization_id: uuid.UUID, actor_id: uuid.UUID | None, name: str) -> CeipalImport:
    imp = CeipalImport(
        organization_id=organization_id,
        status=STAGING,
        name=(name or "Ceipal backup").strip()[:255] or "Ceipal backup",
        created_by=actor_id,
    )
    db.add(imp)
    db.commit()
    db.refresh(imp)
    return imp


def stage_rows(
    db: Session, imp: CeipalImport, *, kind: str, source: str, first_row: int, headers: list[str], rows: list[dict]
) -> int:
    """Stage a batch of one table's rows. `first_row` is the 1-based position
    of rows[0] in its file, so sending the same batch again stages nothing new.
    Returns how many rows the import now holds for this table."""
    if imp.status != STAGING:
        raise ConflictError("This import has already started; start a new one to add more data.")
    table = TABLES_BY_KIND.get(kind)
    if table is None:
        raise ValidationAppError(f"Unknown Ceipal table '{kind}'.")
    if len(rows) > MAX_ROWS_PER_BATCH:
        raise ValidationAppError(f"Send at most {MAX_ROWS_PER_BATCH} rows at a time.")
    missing = [h for h in table.required if not has_header(headers, h)]
    if missing:
        raise ValidationAppError(
            f"{source} does not look like Ceipal's {table.file_stem} table: no {', '.join(missing)} column."
        )
    source = (source or kind)[:255]

    values = []
    for offset, raw in enumerate(rows):
        data = clean_row(raw)
        ref = get(data, table.ref_header) if table.ref_header else ""
        key = get(data, table.key_header) if table.key_header else ""
        if kind == "documents":
            key = _base_name(key)
        values.append(
            {
                "import_id": imp.id,
                "kind": kind,
                "source": source,
                "row_number": first_row + offset,
                "ref": ref[:100] or None,
                "key": key[:500] or None,
                "data": data,
                "status": PENDING,
            }
        )
    if values:
        db.execute(pg_insert(CeipalRow).values(values).on_conflict_do_nothing(constraint="uq_ceipal_rows_position"))
    imp.updated_at = _now()
    db.commit()
    return db.scalar(select(func.count()).where(CeipalRow.import_id == imp.id, CeipalRow.kind == kind)) or 0


def staged_counts(db: Session, imp: CeipalImport) -> dict[str, int]:
    rows = db.execute(
        select(CeipalRow.kind, func.count()).where(CeipalRow.import_id == imp.id).group_by(CeipalRow.kind)
    ).all()
    return dict(rows)


# ------------------------------------------------------------------ importing


def _begin(db: Session, imp: CeipalImport) -> None:
    """Close staging: count what is there and set aside child rows whose
    applicant is not in this backup (Ceipal's education table, for one,
    covers every applicant it has ever held)."""
    applicants = db.scalar(select(func.count()).where(CeipalRow.import_id == imp.id, CeipalRow.kind == "applicants"))
    if not applicants:
        raise ValidationAppError("No applicants were found. Include Applicants.csv from the Ceipal backup.")

    known = select(CeipalRow.ref).where(
        CeipalRow.import_id == imp.id, CeipalRow.kind == "applicants", CeipalRow.ref.is_not(None)
    )
    for kind in ("documents", "education", "notes", "submissions"):
        db.execute(
            update(CeipalRow)
            .where(
                CeipalRow.import_id == imp.id,
                CeipalRow.kind == kind,
                (CeipalRow.ref.is_(None)) | (CeipalRow.ref.not_in(known)),
            )
            .values(status=ORPHAN, message="The applicant is not in this backup.")
        )
    # Documents with no file name to match cannot ever be attached.
    db.execute(
        update(CeipalRow)
        .where(CeipalRow.import_id == imp.id, CeipalRow.kind == "documents", CeipalRow.key.is_(None))
        .values(status=ORPHAN, message="No file name in the documents index.")
    )

    def count(kind: str, status: str | None = None) -> int:
        query = select(func.count()).where(CeipalRow.import_id == imp.id, CeipalRow.kind == kind)
        if status:
            query = query.where(CeipalRow.status == status)
        return db.scalar(query) or 0

    imp.applicants_total = applicants
    imp.documents_expected = count("documents", PENDING)
    imp.documents_orphaned = count("documents", ORPHAN)
    imp.status = IMPORTING
    db.commit()


class _Lookups:
    """Small tables every chunk needs: Ceipal users and degree names, and our
    users by email (to credit "Created By" to the right person)."""

    def __init__(self, db: Session, imp: CeipalImport):
        self.ceipal_users: dict[str, str] = {}
        self.degrees: dict[str, str] = {}
        for kind, key, data in db.execute(
            select(CeipalRow.kind, CeipalRow.key, CeipalRow.data).where(
                CeipalRow.import_id == imp.id, CeipalRow.kind.in_(("users", "degrees"))
            )
        ):
            if not key:
                continue
            if kind == "users":
                self.ceipal_users[key] = get(data, "Email")
            else:
                self.degrees[key] = get(data, "Name")
        emails = {e.lower() for e in self.ceipal_users.values() if e}
        self.our_users: dict[str, uuid.UUID] = {}
        if emails:
            for user_id, email in db.execute(
                select(User.id, User.email).where(
                    User.organization_id == imp.organization_id, func.lower(User.email).in_(emails)
                )
            ):
                self.our_users[email.lower()] = user_id

    def user_label(self, ceipal_user_id: str) -> str:
        """A Ceipal user id as the email Ceipal has for it. -1 is Ceipal's
        own system account (career portal, job boards)."""
        ids = [part.strip() for part in (ceipal_user_id or "").split(",") if part.strip()]
        labels = []
        for uid in ids:
            if uid == "-1":
                labels.append("System")
            else:
                labels.append(self.ceipal_users.get(uid) or uid)
        return ", ".join(labels)

    def our_user(self, ceipal_user_id: str) -> uuid.UUID | None:
        email = self.ceipal_users.get((ceipal_user_id or "").strip(), "").lower()
        return self.our_users.get(email) if email else None


def _profile_fields(data: dict[str, str], lookups: _Lookups) -> dict[str, str]:
    fields = dict(data)
    for column in USER_COLUMNS:
        if fields.get(column):
            fields[column] = lookups.user_label(fields[column])
    return fields


def _candidate_values(data: dict[str, str]) -> dict:
    name = " ".join(p for p in (get(data, "First Name"), get(data, "Middle Name"), get(data, "Last Name")) if p)
    location = ", ".join(p for p in (get(data, "City"), get(data, "State"), get(data, "Country")) if p)
    phone = get(data, "Mobile") or get(data, "Home Phone Number") or get(data, "Work Phone Number")
    return {
        "full_name": (name or get(data, "Nick Name"))[:255],
        "email": _email(get(data, "Email")),
        "phone": _clip(phone, 50),
        "location": _clip(location, 255),
        "current_company": _clip(get(data, "Current Company"), 255),
        "current_title": _clip(get(data, "JOb Title") or get(data, "Job Title"), 255),
        "total_experience_years": _experience_years(get(data, "Experience")),
        "skills": _skills(get(data, "Primary Skills"), get(data, "Skills")),
        "source": _clip(get(data, "Source"), 100),
        "linkedin_url": _clip(get(data, "Linkedin Url"), 500),
        "work_auth": _clip(get(data, "Work Authorization"), 100),
    }


def _education_entry(data: dict[str, str], lookups: _Lookups) -> dict | None:
    level = get(data, "Education")
    degree_name = lookups.degrees.get(level, "") if level else ""
    major = get(data, "Major Study")
    minor = get(data, "Minor Study")
    subject = major + (f" (minor: {minor})" if minor else "")
    degree = " in ".join(p for p in (degree_name, subject) if p)
    school = get(data, "School Name")
    if not degree and not school:
        return None
    return {"degree": degree[:255], "school": school[:255], "year": _year(get(data, "Year Of Completed"))}


def _normalized_code(code: str) -> str:
    return re.sub(r"\s+", "", code or "").upper()


def process_next_chunk(db: Session, imp: CeipalImport) -> CeipalImport:
    """Import the next chunk of applicants. Call until the status leaves
    "importing"; calling again after an interruption carries on."""
    if imp.status == STAGING:
        _begin(db, imp)
    if imp.status != IMPORTING:
        return imp

    staged = list(
        db.scalars(
            select(CeipalRow)
            .where(CeipalRow.import_id == imp.id, CeipalRow.kind == "applicants", CeipalRow.status == PENDING)
            .order_by(CeipalRow.id)
            .limit(CHUNK_SIZE)
        ).all()
    )
    if not staged:
        imp.status = DOCUMENTS if imp.documents_expected else COMPLETED
        db.commit()
        return imp

    lookups = _Lookups(db, imp)
    refs = [r.ref for r in staged if r.ref]
    children: dict[tuple[str, str], list[CeipalRow]] = {}
    for row in db.scalars(
        select(CeipalRow)
        .where(
            CeipalRow.import_id == imp.id,
            CeipalRow.kind.in_(("education", "notes", "submissions")),
            CeipalRow.ref.in_(refs),
            CeipalRow.status == PENDING,
        )
        .order_by(CeipalRow.id)
    ):
        children.setdefault((row.kind, row.ref), []).append(row)

    submission_notes: dict[str, list[dict]] = {}
    submission_ids = [r.key for rows in children.values() for r in rows if r.kind == "submissions" and r.key]
    if submission_ids:
        for key, data in db.execute(
            select(CeipalRow.key, CeipalRow.data).where(
                CeipalRow.import_id == imp.id, CeipalRow.kind == "submission_notes", CeipalRow.key.in_(submission_ids)
            )
        ):
            submission_notes.setdefault(key, []).append(data)

    profiles = {
        p.ceipal_id: p
        for p in db.scalars(
            select(CeipalProfile).where(
                CeipalProfile.organization_id == imp.organization_id, CeipalProfile.ceipal_id.in_(refs)
            )
        )
    }
    emails = {_email(get(r.data, "Email")) for r in staged} - {None}
    by_email: dict[str, Candidate] = {}
    if emails:
        for candidate in db.scalars(
            select(Candidate)
            .where(
                Candidate.organization_id == imp.organization_id,
                Candidate.deleted_at.is_(None),
                func.lower(Candidate.email).in_(emails),
            )
            .order_by(Candidate.created_at)
        ):
            by_email.setdefault(candidate.email.lower(), candidate)

    for row in staged:
        _import_applicant(db, imp, row, lookups, profiles, by_email, children, submission_notes)

    imp.applicants_processed += len(staged)
    db.commit()
    return imp


def _import_applicant(db, imp, row, lookups, profiles, by_email, children, submission_notes) -> None:
    data = row.data
    values = _candidate_values(data)
    if not row.ref:
        row.status, row.message = REJECTED, "No Id."
        imp.rejected_count += 1
        return
    if not values["full_name"]:
        row.status, row.message = REJECTED, "No name."
        imp.rejected_count += 1
        return

    profile = profiles.get(row.ref)
    candidate = profile.candidate if profile is not None else None
    created_candidate = False
    new_profile = profile is None
    if candidate is None and values["email"]:
        candidate = by_email.get(values["email"])
        # Two Ceipal applicants can share an email (Ceipal does not stop it).
        # Each keeps its own candidate rather than one overwriting the other.
        if candidate is not None and db.scalar(select(CeipalProfile.id).where(CeipalProfile.candidate_id == candidate.id)):
            candidate = None

    created_at = _parse_datetime(get(data, "Created At"))
    if candidate is None:
        candidate = Candidate(
            organization_id=imp.organization_id,
            status=CandidateStatus.ACTIVE.value,
            relocation_ok=False,
            created_by=lookups.our_user(get(data, "Created By")) or imp.created_by,
            **values,
        )
        if created_at:
            candidate.created_at = created_at
        db.add(candidate)
        db.flush()
        created_candidate = True
        imp.created_count += 1
    else:
        # Ceipal is the record of truth for a candidate it brought in; for one
        # that was here first, it only fills what is missing.
        overwrite = profile is not None
        for field, value in values.items():
            if value in (None, "", []):
                continue
            if overwrite or not getattr(candidate, field):
                setattr(candidate, field, value)
        candidate.updated_by = imp.created_by
        imp.updated_count += 1

    candidate.origin = ORIGIN
    candidate.external_id = row.ref[:100]
    if values["email"]:
        by_email.setdefault(values["email"], candidate)

    if new_profile:
        profile = CeipalProfile(
            organization_id=imp.organization_id,
            candidate_id=candidate.id,
            ceipal_id=row.ref,
            created_import_id=imp.id,
            candidate_created=created_candidate,
            submissions=[],
        )
        db.add(profile)
        profiles[row.ref] = profile
    profile.fields = _profile_fields(data, lookups)
    profile.last_import_id = imp.id

    # Education and notes are taken once, when Ceipal first brings the
    # candidate in; re-importing the next month's backup must not double them.
    for child in children.get(("education", row.ref), []):
        entry = _education_entry(child.data, lookups) if new_profile else None
        if entry:
            db.add(CandidateEducation(candidate_id=candidate.id, **entry))
            imp.education_count += 1
        child.status = IMPORTED
        child.record_id = candidate.id
    for child in children.get(("notes", row.ref), []):
        subject, note = get(child.data, "Subject"), get(child.data, "Note")
        body = "\n".join(p for p in (subject, note) if p)
        if new_profile and body:
            db.add(
                CandidateNote(
                    candidate_id=candidate.id,
                    body=f"From Ceipal ({lookups.user_label(get(child.data, 'Created By')) or 'unknown'}): {body}",
                    created_at=_parse_datetime(get(child.data, "Created At")) or _now(),
                )
            )
        child.status = IMPORTED
        child.record_id = candidate.id

    submissions = {s.get("submission_id"): s for s in profile.submissions or []}
    for child in children.get(("submissions", row.ref), []):
        entry = _submission_entry(child.data, lookups, submission_notes.get(child.key or "", []))
        previous = submissions.get(entry["submission_id"])
        if previous and previous.get("application_id"):
            entry["application_id"] = previous["application_id"]
            entry["job_title"] = previous.get("job_title")
        else:
            _link_submission(db, imp, candidate, entry, child)
        submissions[entry["submission_id"]] = entry
        imp.submissions_count += 1
        child.status = IMPORTED
    profile.submissions = list(submissions.values())

    row.status = IMPORTED
    row.record_id = candidate.id


def _submission_entry(data: dict[str, str], lookups: _Lookups, notes: list[dict]) -> dict:
    return {
        "submission_id": get(data, "Submission Id") or get(data, "Id"),
        "job_id": get(data, "Job Id"),
        "job_code": get(data, "Job Code"),
        "record_type": get(data, "Record Type"),
        "status": get(data, "Profile Status"),
        "source": get(data, "Source"),
        "submitted_by": lookups.user_label(get(data, "Submitted By")),
        "submitted_on": get(data, "Submitted On"),
        "pay_rate": get(data, "Pay Rate"),
        "bill_rate": get(data, "Bill Rate"),
        "rating": get(data, "Submission Rating"),
        "resume": get(data, "Resume"),
        "date_available": get(data, "Date of Available"),
        "notes": [
            {
                "subject": get(n, "Subject"),
                "note": get(n, "Note"),
                "created_by": lookups.user_label(get(n, "Created By")),
                "created_at": get(n, "Created At"),
            }
            for n in notes
        ],
        "application_id": None,
        "job_title": None,
    }


def _link_submission(db: Session, imp: CeipalImport, candidate: Candidate, entry: dict, child: CeipalRow) -> None:
    """A submission to a Ceipal job we also have (same requisition code)
    becomes an application to it. No AI review is started for it."""
    code = _normalized_code(entry["job_code"])
    if not code:
        return
    job = db.scalar(
        select(Job).where(
            Job.organization_id == imp.organization_id,
            func.upper(func.regexp_replace(Job.req_id, r"\s+", "", "g")) == code,
        )
    )
    if job is None:
        return
    application = db.scalar(
        select(Application).where(Application.candidate_id == candidate.id, Application.job_id == job.id)
    )
    if application is None:
        first_stage = job.stage_template.stages[0] if job.stage_template and job.stage_template.stages else None
        application = Application(
            organization_id=imp.organization_id,
            candidate_id=candidate.id,
            job_id=job.id,
            current_stage_id=first_stage.id if first_stage else None,
            source="Ceipal",
        )
        submitted = _parse_datetime(entry["submitted_on"])
        if submitted:
            application.applied_at = submitted
        db.add(application)
        db.flush()
        child.record_id = application.id
        imp.submissions_linked += 1
    entry["application_id"] = str(application.id)
    entry["job_title"] = job.title


# ------------------------------------------------------------------ documents


def pending_documents(db: Session, imp: CeipalImport, *, offset: int = 0, limit: int = 5000) -> list[str]:
    """Stored file names still waiting for their file, for the browser to
    pick out of the ZIP parts."""
    return list(
        db.scalars(
            select(CeipalRow.key)
            .where(CeipalRow.import_id == imp.id, CeipalRow.kind == "documents", CeipalRow.status == PENDING)
            .order_by(CeipalRow.id)
            .offset(offset)
            .limit(limit)
        ).all()
    )


def _looks_like(data: bytes, extension: str) -> bool:
    signatures = _SIGNATURES.get(extension)
    return signatures is None or any(data.startswith(s) for s in signatures)


def attach_document(db: Session, imp: CeipalImport, *, file_name: str, data: bytes) -> tuple[str, str]:
    """Attach one résumé file. Returns (outcome, message): outcome is
    "attached", "skipped" (already attached, or not one this backup lists)
    or "rejected" (listed, but not a usable file)."""
    if imp.status not in (DOCUMENTS, COMPLETED):
        raise ConflictError("Import the candidates before their documents.")
    key = _base_name(file_name)
    row = db.scalar(
        select(CeipalRow)
        .where(CeipalRow.import_id == imp.id, CeipalRow.kind == "documents", CeipalRow.key == key)
        .order_by(CeipalRow.status != PENDING, CeipalRow.id)
        .limit(1)
        .with_for_update()
    )
    if row is None:
        db.rollback()
        return "skipped", "Not listed in the backup's documents index."
    if row.status != PENDING:
        message = "Already attached." if row.status == ATTACHED else (row.message or "Not importable.")
        db.rollback()
        return "skipped", message

    extension = _extension(key)
    problem = None
    if extension not in _CONTENT_TYPES:
        problem = f"Unsupported file type '{extension or '(none)'}'."
    elif not data:
        problem = "The file is empty."
    elif len(data) > MAX_DOCUMENT_BYTES:
        problem = f"The file is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB."
    elif not _looks_like(data, extension):
        problem = f"The file is not a valid {extension[1:].upper()}."
    profile = db.scalar(
        select(CeipalProfile).where(CeipalProfile.organization_id == imp.organization_id, CeipalProfile.ceipal_id == row.ref)
    )
    if problem is None and profile is None:
        problem = "The applicant was not imported."
    if problem:
        row.status, row.message = REJECTED, problem
        db.commit()
        return "rejected", problem

    is_resume = get(row.data, "Document Type").strip().lower() == "resume"
    display_name = (get(row.data, "Orignal Document Name") or get(row.data, "Original Document Name") or key)[:400]
    storage_key = build_storage_key(profile.candidate_id, key)
    upload_bytes(storage_key, data, _CONTENT_TYPES[extension])
    document = CandidateDocument(
        candidate_id=profile.candidate_id,
        document_type=(CandidateDocumentType.RESUME if is_resume else CandidateDocumentType.OTHER).value,
        file_name=display_name,
        content_type=_CONTENT_TYPES[extension],
        size_bytes=len(data),
        storage_key=storage_key,
        uploaded_by=imp.created_by,
    )
    db.add(document)
    db.flush()
    if is_resume and (get(row.data, "Default Resume") == "1" or profile.resume_document_id is None):
        profile.resume_document_id = document.id
    row.status, row.message, row.record_id = ATTACHED, None, document.id
    db.execute(
        update(CeipalImport)
        .where(CeipalImport.id == imp.id)
        .values(documents_attached=CeipalImport.documents_attached + 1, updated_at=_now())
    )
    db.commit()
    return "attached", display_name


def finish(db: Session, imp: CeipalImport) -> CeipalImport:
    if imp.status == DOCUMENTS:
        imp.status = COMPLETED
        db.commit()
    elif imp.status != COMPLETED:
        raise ConflictError("The candidates have not finished importing yet.")
    return imp


# ------------------------------------------------------------------ report


def report_rows(db: Session, imp: CeipalImport) -> Iterator[str]:
    """Everything that did not come in, and why, as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    writer.writerow(["Table", "File", "Row", "Applicant (Ceipal Id)", "Name / file", "Problem"])
    yield "﻿" + flush()
    query = (
        select(CeipalRow)
        .where(
            CeipalRow.import_id == imp.id,
            CeipalRow.kind.in_(("applicants", "documents")),
            (CeipalRow.status.in_((REJECTED, ORPHAN))) | ((CeipalRow.kind == "documents") & (CeipalRow.status == PENDING)),
        )
        .order_by(CeipalRow.kind, CeipalRow.id)
        .execution_options(yield_per=1000)
    )
    for row in db.scalars(query):
        if row.kind == "applicants":
            label = " ".join(p for p in (get(row.data, "First Name"), get(row.data, "Last Name")) if p)
        else:
            label = row.key or ""
        message = row.message or ("The file was not found in the documents ZIP." if row.status == PENDING else "")
        writer.writerow([row.kind, row.source, row.row_number, row.ref or "", label, message])
        yield flush()


# ------------------------------------------------------------------ undo


def undo_import(db: Session, imp: CeipalImport, *, time_budget_seconds: float = 30.0) -> CeipalImport:
    """Delete what this import brought in, stored files included, a batch at
    a time: call until the status is "undone".

    Candidates it created go, unless something since depends on them (an
    application made here, a bench profile, a message). Candidates that were
    here before keep their record but lose what the import attached to them.
    """
    if imp.status not in (IMPORTING, DOCUMENTS, COMPLETED, UNDOING):
        raise ConflictError("Only an import that has run can be undone.")
    imp.status = UNDOING
    db.commit()
    started = time.monotonic()

    # First the candidates and profiles it brought in. (while/else: the else
    # runs when the time budget, not the work, ran out.)
    while time.monotonic() - started < time_budget_seconds:
        profiles = list(
            db.scalars(
                select(CeipalProfile)
                .where(CeipalProfile.organization_id == imp.organization_id, CeipalProfile.created_import_id == imp.id)
                .limit(CHUNK_SIZE)
            ).all()
        )
        if not profiles:
            break
        created = [p.candidate_id for p in profiles if p.candidate_created]
        in_use = _in_use(db, imp, created)
        for profile in profiles:
            candidate = db.get(Candidate, profile.candidate_id)
            if profile.candidate_created and profile.candidate_id not in in_use:
                for document in candidate.documents:
                    delete_object(document.storage_key)
                db.delete(candidate)
                continue
            if profile.candidate_created:
                imp.kept_on_undo += 1
            else:
                candidate.origin = None
            profile.created_import_id = None
            if not profile.candidate_created:
                db.delete(profile)
        db.commit()
    else:
        return imp

    # What it attached to candidates that are staying.
    while time.monotonic() - started < time_budget_seconds:
        rows = list(
            db.scalars(
                select(CeipalRow)
                .where(
                    CeipalRow.import_id == imp.id,
                    CeipalRow.kind.in_(("documents", "submissions")),
                    CeipalRow.record_id.is_not(None),
                )
                .limit(CHUNK_SIZE)
            ).all()
        )
        if not rows:
            imp.status = UNDONE
            db.commit()
            return imp
        for row in rows:
            if row.kind == "documents":
                document = db.get(CandidateDocument, row.record_id)
                if document is not None:
                    delete_object(document.storage_key)
                    db.delete(document)
            else:
                application = db.get(Application, row.record_id)
                if application is not None and not _application_in_use(db, application):
                    db.delete(application)
            row.record_id = None
        db.commit()
    return imp


def _in_use(db: Session, imp: CeipalImport, candidate_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not candidate_ids:
        return set()
    own_applications = select(CeipalRow.record_id).where(
        CeipalRow.import_id == imp.id, CeipalRow.kind == "submissions", CeipalRow.record_id.is_not(None)
    )
    used: set[uuid.UUID] = set()
    used.update(
        db.scalars(
            select(Application.candidate_id).where(
                Application.candidate_id.in_(candidate_ids), Application.id.not_in(own_applications)
            )
        )
    )
    # An application this import made that has since moved on in the pipeline
    # counts as use too.
    used.update(
        db.scalars(
            select(Application.candidate_id).where(
                Application.candidate_id.in_(candidate_ids),
                Application.id.in_(own_applications),
                Application.updated_at > Application.created_at,
            )
        )
    )
    used.update(db.scalars(select(BenchProfile.candidate_id).where(BenchProfile.candidate_id.in_(candidate_ids))))
    used.update(db.scalars(select(OutboundMessage.candidate_id).where(OutboundMessage.candidate_id.in_(candidate_ids))))
    return used


def _application_in_use(db: Session, application: Application) -> bool:
    return application.updated_at > application.created_at


# ------------------------------------------------------------------ the Ceipal view


def columns_for(profiles: list[CeipalProfile]) -> list[str]:
    columns = list(APPLICANT_COLUMNS)
    known = {c.lower() for c in columns}
    for profile in profiles:
        for header in profile.fields or {}:
            if header.lower() not in known:
                known.add(header.lower())
                columns.append(header)
    return columns


def delete_staged_rows(db: Session, imp: CeipalImport) -> None:
    """Staged rows are only needed while an import can still change; once it
    is undone they are dead weight."""
    db.execute(delete(CeipalRow).where(CeipalRow.import_id == imp.id))
    db.commit()
