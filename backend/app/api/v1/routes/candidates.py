import uuid

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.api.v1.routes._documents import document_response
from app.core.enums import AuditAction, CandidateDocumentType, PermissionAction, PermissionResource
from app.core.file_validation import validate_document_size, validate_resume_upload
from app.core.pagination import PageParams, page_params, paginate
from app.schemas.application import ApplicationRead
from app.schemas.auth import CurrentUser
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDocumentRead,
    CandidateNoteCreate,
    CandidateNoteRead,
    CandidateRead,
    CandidateTagsUpdate,
    CandidateUpdate,
    DuplicateWarning,
)
from app.schemas.communication import OutboundMessageRead, SendMessageRequest
from app.services.applications.service import list_applications
from app.services.audit.service import record as record_audit
from app.services.candidates import service as candidate_service
from app.services.communication import service as communication_service
from app.workers.dispatch import dispatch
from app.workers.tasks.mail import send_outbound_message_task

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _to_read(candidate, duplicate_warnings=None) -> CandidateRead:
    return CandidateRead(
        id=candidate.id,
        organization_id=candidate.organization_id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        current_company=candidate.current_company,
        current_title=candidate.current_title,
        total_experience_years=candidate.total_experience_years,
        relevant_experience_years=candidate.relevant_experience_years,
        notice_period=candidate.notice_period,
        current_ctc=candidate.current_ctc,
        expected_ctc=candidate.expected_ctc,
        skills=candidate.skills,
        source=candidate.source,
        rating=candidate.rating,
        linkedin_url=candidate.linkedin_url,
        work_auth=candidate.work_auth,
        relocation_ok=candidate.relocation_ok,
        status=candidate.status,
        education=[{"degree": e.degree, "school": e.school, "year": e.year} for e in candidate.education],
        tags=[t.tag for t in candidate.tags],
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        duplicate_warnings=duplicate_warnings or [],
    )


@router.get("", response_model=list[CandidateRead])
def list_candidates(
    response: Response,
    status: str | None = None,
    pool: bool = False,
    search: str | None = None,
    pagination: PageParams = Depends(page_params),
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[CandidateRead]:
    query = candidate_service.build_candidates_query(
        current_user.organization_id, status=status, talent_pool_only=pool, search=search, viewer=current_user
    )
    candidates, total = paginate(db, query, pagination)
    # Body stays a plain array for backward compatibility; the total rides on
    # a header so a caller that wants "load more" / page controls can read it
    # without every existing consumer needing to switch to an envelope shape.
    response.headers["X-Total-Count"] = str(total)
    return [_to_read(c) for c in candidates]


@router.post("", response_model=CandidateRead, status_code=201)
def create_candidate(
    payload: CandidateCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> CandidateRead:
    data = payload.model_dump()
    email = data.pop("email")
    phone = data.pop("phone")
    education = data.pop("education")
    tags = data.pop("tags")

    candidate, duplicates = candidate_service.create_candidate(
        db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        email=email,
        phone=phone,
        education=education,
        tags=tags,
        **data,
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.CANDIDATE_CREATED.value,
        resource_type="candidate",
        resource_id=str(candidate.id),
    )
    db.commit()
    db.refresh(candidate)
    warnings = [
        DuplicateWarning(candidate_id=d.id, full_name=d.full_name, email=d.email, match_reason="email_or_phone")
        for d in duplicates
    ]
    return _to_read(candidate, warnings)


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> CandidateRead:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    return _to_read(candidate)


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> CandidateRead:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    candidate = candidate_service.update_candidate(
        db, candidate, actor_id=current_user.id, **payload.model_dump(exclude_unset=True)
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.CANDIDATE_UPDATED.value,
        resource_type="candidate",
        resource_id=str(candidate.id),
    )
    db.commit()
    return _to_read(candidate)


@router.post("/{candidate_id}/documents", response_model=CandidateDocumentRead, status_code=201)
async def upload_document(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: str = Form(CandidateDocumentType.RESUME.value),
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> CandidateDocumentRead:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    data = await file.read()
    file_name = file.filename or "document"
    if document_type == CandidateDocumentType.RESUME.value:
        # Résumés are format-restricted to PDF/DOC/DOCX with a magic-byte
        # check; this also covers the size cap.
        validate_resume_upload(data=data, file_name=file_name)
    else:
        # "Other" documents (offer letters signed elsewhere, ID scans, etc.)
        # aren't limited to a specific format, but every upload still gets a
        # blanket size cap so nothing fills the disk regardless of type.
        validate_document_size(data=data)
    document = candidate_service.add_document(
        db,
        candidate,
        document_type=document_type,
        file_name=file_name,
        content_type=file.content_type or "application/octet-stream",
        data=data,
        uploaded_by=current_user.id,
    )
    return document


@router.get("/{candidate_id}/documents", response_model=list[CandidateDocumentRead])
def list_documents(
    candidate_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[CandidateDocumentRead]:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    return candidate_service.list_documents(db, candidate)


@router.get("/{candidate_id}/documents/{document_id}/download")
def download_document(
    candidate_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> Response:
    # get_candidate applies the same row-level scoping as every other read of
    # this record, so a recruiter who cannot see the candidate cannot reach
    # their resume either.
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    document = candidate_service.get_document(db, candidate, document_id)
    return document_response(
        storage_key=document.storage_key,
        file_name=document.file_name,
        content_type=document.content_type,
    )


@router.post("/{candidate_id}/notes", response_model=CandidateNoteRead, status_code=201)
def add_note(
    candidate_id: uuid.UUID,
    payload: CandidateNoteCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> CandidateNoteRead:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    note = candidate_service.add_note(db, candidate, author_id=current_user.id, body=payload.body)
    return note


@router.get("/{candidate_id}/notes", response_model=list[CandidateNoteRead])
def list_notes(
    candidate_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[CandidateNoteRead]:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    return candidate_service.list_notes(db, candidate)


@router.post("/{candidate_id}/tags", response_model=CandidateRead)
def set_tags(
    candidate_id: uuid.UUID,
    payload: CandidateTagsUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> CandidateRead:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    candidate = candidate_service.set_tags(db, candidate, payload.tags)
    return _to_read(candidate)


@router.get("/{candidate_id}/applications", response_model=list[ApplicationRead])
def candidate_applications(
    candidate_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ApplicationRead]:
    candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    return list_applications(db, current_user.organization_id, candidate_id=candidate_id, viewer=current_user)


@router.get("/{candidate_id}/messages", response_model=list[OutboundMessageRead])
def list_messages(
    candidate_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[OutboundMessageRead]:
    candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    return communication_service.list_messages(db, current_user.organization_id, candidate_id=candidate_id)


@router.post("/{candidate_id}/messages", response_model=OutboundMessageRead, status_code=201)
def send_message(
    candidate_id: uuid.UUID,
    payload: SendMessageRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OutboundMessageRead:
    candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    message = communication_service.log_message(
        db,
        organization_id=current_user.organization_id,
        sent_by=current_user.id,
        candidate_id=candidate_id,
        application_id=payload.application_id,
        template_id=payload.template_id,
        subject=payload.subject,
        body=payload.body,
    )
    # The row is always written first, so the outreach is recorded even if
    # delivery later fails; the worker flips status to sent/failed.
    dispatch(send_outbound_message_task, str(message.id))
    return message
