"""Ceipal backup import, and the Ceipal view of the candidate list.

The import is for Admins and Super Admins, like every other bulk import: it
brings in the whole of a Ceipal account's applicants at once. The Ceipal view
is a candidate list, so it needs what any candidate list needs.

The backup's ZIPs never reach this API whole -- they run to gigabytes, and a
Cloud Run request stops at 32 MB. The browser opens them and sends the CSV
tables as row batches (POST .../rows) and the résumés a few files at a time
(POST .../documents).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db_session, require_permission
from app.api.v1.routes.imports import _safe_name, require_admin
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.file_validation import MAX_DOCUMENT_BYTES
from app.db.models.candidate import Candidate
from app.db.models.ceipal import CeipalProfile
from app.schemas.auth import CurrentUser
from app.services.audit.service import record as record_audit
from app.services.candidates import service as candidate_service
from app.services.ceipal import service as ceipal_service
from app.services.ceipal.rules import CEIPAL_ORIGIN

router = APIRouter(tags=["ceipal"])

# Per request, so one documents upload stays well inside Cloud Run's 32 MB.
MAX_FILES_PER_REQUEST = 20
MAX_REQUEST_DOCUMENT_BYTES = 24 * 1024 * 1024


# ------------------------------------------------------------------ schemas


class CeipalImportRead(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    applicants_total: int
    applicants_processed: int
    created_count: int
    updated_count: int
    rejected_count: int
    documents_expected: int
    documents_attached: int
    documents_orphaned: int
    education_count: int
    submissions_count: int
    submissions_linked: int
    kept_on_undo: int
    staged: dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreateImportRequest(BaseModel):
    name: str = Field(default="Ceipal backup", max_length=255)


class StageRowsRequest(BaseModel):
    kind: str
    # The file the rows came from, e.g. "backup_part1.zip/Applicants.csv".
    source: str = Field(max_length=255)
    # 1-based position of rows[0] in that file.
    first_row: int = Field(ge=1)
    headers: list[str]
    rows: list[dict[str, str | None]]


class StageRowsResponse(BaseModel):
    kind: str
    staged: int


class PendingDocuments(BaseModel):
    names: list[str]
    total_pending: int


class DocumentResult(BaseModel):
    file_name: str
    outcome: str
    message: str


class DocumentsResponse(BaseModel):
    results: list[DocumentResult]
    job: CeipalImportRead


class ResumeRef(BaseModel):
    document_id: uuid.UUID
    file_name: str


class CeipalCandidateRow(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    values: dict[str, str]
    resume: ResumeRef | None


class CeipalCandidatePage(BaseModel):
    columns: list[str]
    total: int
    rows: list[CeipalCandidateRow]


class CeipalProfileRead(BaseModel):
    candidate_id: uuid.UUID
    ceipal_id: str
    columns: list[str]
    values: dict[str, str]
    # Columns corrected in this app since the import, and those never editable.
    edited_columns: list[str] = []
    read_only_columns: list[str] = []
    submissions: list[dict]
    resume: ResumeRef | None


def _read(db: Session, imp) -> CeipalImportRead:
    result = CeipalImportRead.model_validate(imp)
    if imp.status == ceipal_service.STAGING:
        result.staged = ceipal_service.staged_counts(db, imp)
    return result


def _audit(db: Session, current_user: CurrentUser, imp, action: str, **metadata) -> None:
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=action,
        resource_type="ceipal_import",
        resource_id=str(imp.id),
        metadata={"name": imp.name, **metadata},
    )
    db.commit()


# ------------------------------------------------------------------ import


@router.post("/imports/ceipal", response_model=CeipalImportRead, status_code=201)
def create_ceipal_import(
    payload: CreateImportRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> CeipalImportRead:
    imp = ceipal_service.create_import(
        db, organization_id=current_user.organization_id, actor_id=current_user.id, name=payload.name
    )
    return _read(db, imp)


@router.get("/imports/ceipal", response_model=list[CeipalImportRead])
def list_ceipal_imports(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> list[CeipalImportRead]:
    return [_read(db, imp) for imp in ceipal_service.list_imports(db, current_user.organization_id, limit)]


@router.get("/imports/ceipal/{import_id}", response_model=CeipalImportRead)
def get_ceipal_import(
    import_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> CeipalImportRead:
    return _read(db, ceipal_service.get_import(db, current_user.organization_id, import_id))


@router.post("/imports/ceipal/{import_id}/rows", response_model=StageRowsResponse)
def stage_ceipal_rows(
    import_id: uuid.UUID,
    payload: StageRowsRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> StageRowsResponse:
    """Stage a batch of one table's rows. Safe to send again."""
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    staged = ceipal_service.stage_rows(
        db,
        imp,
        kind=payload.kind,
        source=payload.source,
        first_row=payload.first_row,
        headers=payload.headers,
        rows=payload.rows,
    )
    return StageRowsResponse(kind=payload.kind, staged=staged)


@router.post("/imports/ceipal/{import_id}/process", response_model=CeipalImportRead)
def process_ceipal_import(
    import_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> CeipalImportRead:
    """Import the next chunk of applicants. Call until the status is
    "documents" or "completed"."""
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    before = imp.status
    imp = ceipal_service.process_next_chunk(db, imp)
    if before == ceipal_service.STAGING:
        _audit(db, current_user, imp, AuditAction.DATA_IMPORTED.value, phase="started", applicants=imp.applicants_total)
    if before != ceipal_service.COMPLETED and imp.status == ceipal_service.COMPLETED:
        # No documents to wait for: the import finished here.
        _audit(db, current_user, imp, AuditAction.DATA_IMPORTED.value, phase="completed", created=imp.created_count)
    return _read(db, imp)


@router.get("/imports/ceipal/{import_id}/documents/pending", response_model=PendingDocuments)
def pending_ceipal_documents(
    import_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=5000, ge=1, le=20000),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> PendingDocuments:
    """The stored file names still waiting for their file."""
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    names = ceipal_service.pending_documents(db, imp, offset=offset, limit=limit)
    remaining = imp.documents_expected - imp.documents_attached
    return PendingDocuments(names=names, total_pending=max(remaining, 0))


@router.post("/imports/ceipal/{import_id}/documents", response_model=DocumentsResponse)
async def upload_ceipal_documents(
    import_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> DocumentsResponse:
    """Attach résumé files, matched by the name Ceipal stored them under.
    Files not in the backup's documents index are skipped, so a whole ZIP
    part can be sent through without picking."""
    if len(files) > MAX_FILES_PER_REQUEST:
        raise ValidationAppError(f"Send at most {MAX_FILES_PER_REQUEST} files at a time.")
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    results: list[DocumentResult] = []
    total = 0
    for upload in files:
        name = upload.filename or "file"
        data = await upload.read(MAX_DOCUMENT_BYTES + 1)
        total += len(data)
        if total > MAX_REQUEST_DOCUMENT_BYTES + MAX_DOCUMENT_BYTES:
            raise ValidationAppError("Too much in one request; send fewer files at a time.")
        outcome, message = ceipal_service.attach_document(db, imp, file_name=name, data=data)
        results.append(DocumentResult(file_name=name, outcome=outcome, message=message))
    db.refresh(imp)
    return DocumentsResponse(results=results, job=_read(db, imp))


@router.post("/imports/ceipal/{import_id}/finish", response_model=CeipalImportRead)
def finish_ceipal_import(
    import_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> CeipalImportRead:
    """Mark the import done. Documents can still be added afterwards, from a
    ZIP part that turns up later."""
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    was_completed = imp.status == ceipal_service.COMPLETED
    imp = ceipal_service.finish(db, imp)
    if not was_completed:
        _audit(
            db,
            current_user,
            imp,
            AuditAction.DATA_IMPORTED.value,
            phase="completed",
            created=imp.created_count,
            updated=imp.updated_count,
            documents=imp.documents_attached,
        )
    return _read(db, imp)


@router.get("/imports/ceipal/{import_id}/report")
def ceipal_import_report(
    import_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    """Applicants not imported and documents not attached, with the reason."""
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    return StreamingResponse(
        ceipal_service.report_rows(db, imp),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(imp.name)}-not-imported.csv"'},
    )


@router.post("/imports/ceipal/{import_id}/undo", response_model=CeipalImportRead)
def undo_ceipal_import(
    import_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> CeipalImportRead:
    """Undo, a batch at a time: call until the status is "undone"."""
    imp = ceipal_service.get_import(db, current_user.organization_id, import_id)
    imp = ceipal_service.undo_import(db, imp)
    if imp.status == ceipal_service.UNDONE:
        _audit(db, current_user, imp, AuditAction.DATA_IMPORT_UNDONE.value, kept_in_use=imp.kept_on_undo)
    return _read(db, imp)


# ------------------------------------------------------------------ the Ceipal view


def _resume(profile: CeipalProfile) -> ResumeRef | None:
    document = profile.resume_document
    if document is None:
        return None
    return ResumeRef(document_id=document.id, file_name=document.file_name)


@router.get("/ceipal/candidates", response_model=CeipalCandidatePage)
def list_ceipal_candidates(
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> CeipalCandidatePage:
    """Candidates imported from Ceipal, with every Ceipal column."""
    base = candidate_service.build_candidates_query(
        current_user.organization_id, search=search, viewer=current_user, origin=CEIPAL_ORIGIN
    )
    ids = base.with_only_columns(Candidate.id).order_by(None)
    total = db.scalar(select(func.count()).select_from(ids.subquery())) or 0
    page = list(
        db.scalars(
            select(CeipalProfile)
            .join(Candidate, Candidate.id == CeipalProfile.candidate_id)
            .where(CeipalProfile.candidate_id.in_(ids))
            .options(selectinload(CeipalProfile.resume_document), selectinload(CeipalProfile.candidate))
            .order_by(Candidate.created_at.desc(), Candidate.id)
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return CeipalCandidatePage(
        columns=ceipal_service.columns_for(page),
        total=total,
        rows=[
            CeipalCandidateRow(
                candidate_id=p.candidate_id,
                full_name=p.candidate.full_name,
                values={k: str(v) for k, v in (p.fields or {}).items()},
                resume=_resume(p),
            )
            for p in page
        ],
    )


@router.get("/ceipal/candidates/{candidate_id}", response_model=CeipalProfileRead)
def get_ceipal_profile(
    candidate_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> CeipalProfileRead:
    return _profile_read(_profile_for(db, current_user, candidate_id))


class CeipalProfileUpdate(BaseModel):
    # Ceipal header -> corrected value.
    values: dict[str, str] = Field(max_length=200)


@router.patch("/ceipal/candidates/{candidate_id}", response_model=CeipalProfileRead)
def update_ceipal_profile(
    candidate_id: uuid.UUID,
    payload: CeipalProfileUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CANDIDATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> CeipalProfileRead:
    """Correct or complete a migrated Ceipal record. Résumé and document
    downloads stay governed by the separate download permission."""
    profile = _profile_for(db, current_user, candidate_id)
    profile = ceipal_service.edit_profile(db, profile, actor_id=current_user.id, values=payload.values)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.CANDIDATE_UPDATED.value,
        resource_type="candidate",
        resource_id=str(profile.candidate_id),
        metadata={"ceipal_columns": sorted(payload.values)},
    )
    db.commit()
    return _profile_read(profile)


def _profile_for(db: Session, current_user: CurrentUser, candidate_id: uuid.UUID) -> CeipalProfile:
    candidate = candidate_service.get_candidate(db, current_user.organization_id, candidate_id, viewer=current_user)
    profile = db.scalar(select(CeipalProfile).where(CeipalProfile.candidate_id == candidate.id))
    if profile is None:
        raise NotFoundError("This candidate was not imported from Ceipal")
    return profile


def _profile_read(profile: CeipalProfile) -> CeipalProfileRead:
    columns = ceipal_service.columns_for([profile])
    return CeipalProfileRead(
        candidate_id=profile.candidate_id,
        ceipal_id=profile.ceipal_id,
        columns=columns,
        values={k: str(v) for k, v in (profile.fields or {}).items()},
        edited_columns=list(profile.edited_columns or []),
        read_only_columns=[c for c in columns if c.lower() in ceipal_service.READ_ONLY_COLUMNS],
        submissions=profile.submissions or [],
        resume=_resume(profile),
    )
