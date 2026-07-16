import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import CandidateStatus, DuplicateMatchReason
from app.core.exceptions import NotFoundError
from app.db.models.candidate import (
    Candidate,
    CandidateDocument,
    CandidateEducation,
    CandidateNote,
    CandidateTag,
    DuplicateCandidateLink,
)
from app.services.storage.service import build_storage_key, upload_bytes

_TALENT_POOL_STATUSES = {CandidateStatus.PASSIVE.value, CandidateStatus.SILVER_MEDALIST.value}


def _load(query):
    return query.options(
        selectinload(Candidate.education), selectinload(Candidate.tags), selectinload(Candidate.notes)
    )


def find_duplicates(db: Session, organization_id: uuid.UUID, *, email: str, phone: str | None) -> list[Candidate]:
    match_condition = (Candidate.email == email) | (Candidate.phone == phone) if phone else (Candidate.email == email)
    return list(
        db.scalars(
            select(Candidate).where(
                Candidate.organization_id == organization_id, Candidate.deleted_at.is_(None), match_condition
            )
        ).all()
    )


def create_candidate(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    email: str,
    phone: str | None,
    education: list[dict],
    tags: list[str],
    **fields,
) -> tuple[Candidate, list[Candidate]]:
    duplicates = find_duplicates(db, organization_id, email=email, phone=phone)

    candidate = Candidate(
        organization_id=organization_id, email=email, phone=phone, created_by=actor_id, updated_by=actor_id, **fields
    )
    db.add(candidate)
    db.flush()

    for item in education:
        db.add(CandidateEducation(candidate_id=candidate.id, **item))
    for tag in tags:
        db.add(CandidateTag(candidate_id=candidate.id, tag=tag))

    for duplicate in duplicates:
        reason = DuplicateMatchReason.EMAIL.value if duplicate.email == email else DuplicateMatchReason.PHONE.value
        db.add(
            DuplicateCandidateLink(
                organization_id=organization_id,
                candidate_id=candidate.id,
                duplicate_of_candidate_id=duplicate.id,
                match_reason=reason,
            )
        )

    db.commit()
    db.refresh(candidate)
    return candidate, duplicates


def get_candidate(db: Session, organization_id: uuid.UUID, candidate_id: uuid.UUID) -> Candidate:
    candidate = db.scalar(
        _load(
            select(Candidate).where(
                Candidate.id == candidate_id, Candidate.organization_id == organization_id, Candidate.deleted_at.is_(None)
            )
        )
    )
    if candidate is None:
        raise NotFoundError("Candidate not found")
    return candidate


def list_candidates(
    db: Session,
    organization_id: uuid.UUID,
    *,
    status: str | None = None,
    talent_pool_only: bool = False,
    search: str | None = None,
) -> list[Candidate]:
    query = _load(select(Candidate)).where(
        Candidate.organization_id == organization_id, Candidate.deleted_at.is_(None)
    )
    if status is not None:
        query = query.where(Candidate.status == status)
    if talent_pool_only:
        query = query.where(Candidate.status.in_(_TALENT_POOL_STATUSES))
    if search:
        like = f"%{search}%"
        query = query.where((Candidate.full_name.ilike(like)) | (Candidate.email.ilike(like)))
    query = query.order_by(Candidate.created_at.desc())
    return list(db.scalars(query).all())


def update_candidate(db: Session, candidate: Candidate, *, actor_id: uuid.UUID | None, **fields) -> Candidate:
    for key, value in fields.items():
        if value is not None:
            setattr(candidate, key, value)
    candidate.updated_by = actor_id
    db.commit()
    db.refresh(candidate)
    return candidate


def add_note(db: Session, candidate: Candidate, *, author_id: uuid.UUID | None, body: str) -> CandidateNote:
    note = CandidateNote(candidate_id=candidate.id, author_id=author_id, body=body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, candidate: Candidate) -> list[CandidateNote]:
    return list(
        db.scalars(
            select(CandidateNote)
            .where(CandidateNote.candidate_id == candidate.id)
            .order_by(CandidateNote.created_at.desc())
        ).all()
    )


def set_tags(db: Session, candidate: Candidate, tags: list[str]) -> Candidate:
    for existing in list(candidate.tags):
        db.delete(existing)
    db.flush()
    for tag in dict.fromkeys(tags):
        db.add(CandidateTag(candidate_id=candidate.id, tag=tag))
    db.commit()
    db.refresh(candidate)
    return candidate


def add_document(
    db: Session,
    candidate: Candidate,
    *,
    document_type: str,
    file_name: str,
    content_type: str,
    data: bytes,
    uploaded_by: uuid.UUID | None,
) -> CandidateDocument:
    storage_key = build_storage_key(candidate.id, file_name)
    upload_bytes(storage_key, data, content_type)

    document = CandidateDocument(
        candidate_id=candidate.id,
        document_type=document_type,
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(data),
        storage_key=storage_key,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
