import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import CandidateStatus, DuplicateMatchReason, RoleName
from app.core.exceptions import NotFoundError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.candidate import (
    Candidate,
    CandidateDocument,
    CandidateEducation,
    CandidateNote,
    CandidateTag,
    DuplicateCandidateLink,
)
from app.db.models.interview import Interview, InterviewPanelMember
from app.db.models.job import Job
from app.schemas.auth import CurrentUser
from app.services.storage.service import build_storage_key, upload_bytes

_TALENT_POOL_STATUSES = {CandidateStatus.PASSIVE.value, CandidateStatus.SILVER_MEDALIST.value}


def _scope_filter(query, viewer: CurrentUser | None):
    if viewer is None:
        return query
    scopes = scoped_roles(viewer.roles)
    if not scopes:
        return query

    conditions = []
    if RoleName.HIRING_MANAGER.value in scopes:
        conditions.append(
            Candidate.id.in_(
                select(Application.candidate_id)
                .join(Job, Job.id == Application.job_id)
                .where(Job.hiring_manager_id == viewer.id)
            )
        )
    if RoleName.INTERVIEWER.value in scopes:
        conditions.append(
            Candidate.id.in_(
                select(Application.candidate_id)
                .join(Interview, Interview.application_id == Application.id)
                .join(InterviewPanelMember, InterviewPanelMember.interview_id == Interview.id)
                .where(InterviewPanelMember.user_id == viewer.id)
            )
        )
    return query.where(or_(*conditions))


def _load(query):
    return query.options(selectinload(Candidate.education), selectinload(Candidate.tags), selectinload(Candidate.notes))


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


def get_candidate(
    db: Session, organization_id: uuid.UUID, candidate_id: uuid.UUID, *, viewer: CurrentUser | None = None
) -> Candidate:
    query = _load(
        select(Candidate).where(
            Candidate.id == candidate_id, Candidate.organization_id == organization_id, Candidate.deleted_at.is_(None)
        )
    )
    candidate = db.scalar(_scope_filter(query, viewer))
    if candidate is None:
        raise NotFoundError("Candidate not found")
    return candidate


def build_candidates_query(
    organization_id: uuid.UUID,
    *,
    status: str | None = None,
    talent_pool_only: bool = False,
    search: str | None = None,
    viewer: CurrentUser | None = None,
):
    """Filters + scoping only, unexecuted — shared by the paginated route and
    any caller that still needs the full result set (dropdowns, ID-lookup
    maps). Keeping this separate from execution means both paths stay in sync
    as filters evolve."""
    query = _load(select(Candidate)).where(Candidate.organization_id == organization_id, Candidate.deleted_at.is_(None))
    if status is not None:
        query = query.where(Candidate.status == status)
    if talent_pool_only:
        query = query.where(Candidate.status.in_(_TALENT_POOL_STATUSES))
    if search:
        like = f"%{search}%"
        query = query.where((Candidate.full_name.ilike(like)) | (Candidate.email.ilike(like)))
    query = _scope_filter(query, viewer)
    return query.order_by(Candidate.created_at.desc())


# Safety ceiling for callers that do not paginate explicitly (dropdowns,
# candidate-id lookup maps elsewhere in the app). Real pagination lives in the
# `/candidates` route via `build_candidates_query` + `paginate()`; this just
# stops an unbounded query from shipping the entire table to a client that
# only asked for "give me candidates" with no limit in mind.
_UNPAGINATED_SAFETY_LIMIT = 1000


def list_candidates(
    db: Session,
    organization_id: uuid.UUID,
    *,
    status: str | None = None,
    talent_pool_only: bool = False,
    search: str | None = None,
    viewer: CurrentUser | None = None,
) -> list[Candidate]:
    query = build_candidates_query(
        organization_id, status=status, talent_pool_only=talent_pool_only, search=search, viewer=viewer
    )
    return list(db.scalars(query.limit(_UNPAGINATED_SAFETY_LIMIT)).unique().all())


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
            select(CandidateNote).where(CandidateNote.candidate_id == candidate.id).order_by(CandidateNote.created_at.desc())
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
