"""Bulk import (CSV, Excel, JSON) and export, for Admins and Super Admins.

Bulk data in either direction is the whole organization's records at once --
a 100,000-candidate export is the entire talent database in one file -- so both
are limited to administrators, and every import, undo and export is audited.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.core.enums import AuditAction, RoleName
from app.core.exceptions import ForbiddenError, ValidationAppError
from app.db.models.import_job import ImportJob
from app.schemas.auth import CurrentUser
from app.services.audit.service import record as record_audit
from app.services.imports import service as import_service
from app.services.imports.entities import IMPORTERS
from app.services.imports.parsing import MAX_FILE_BYTES, MAX_ROWS, SUPPORTED_EXTENSIONS

router = APIRouter(tags=["imports"])

_ADMIN_ROLES = {RoleName.SUPER_ADMIN.value, RoleName.ADMIN.value}


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not _ADMIN_ROLES & set(current_user.roles):
        raise ForbiddenError("Only Admins and Super Admins can import or export data.")
    return current_user


# ------------------------------------------------------------------ schemas


class FieldInfo(BaseModel):
    key: str
    label: str
    kind: str
    required: bool
    help: str | None
    choices: list[str]


class EntityInfo(BaseModel):
    key: str
    label: str
    fields: list[FieldInfo]


class ImportLimits(BaseModel):
    max_file_mb: int
    max_rows: int
    extensions: list[str]


class ImportCatalog(BaseModel):
    entities: list[EntityInfo]
    limits: ImportLimits


class ImportJobRead(BaseModel):
    id: uuid.UUID
    entity: str
    status: str
    file_name: str
    columns: list[str]
    mapping: dict[str, str | None]
    duplicate_mode: str
    total_rows: int
    processed_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    rejected_count: int
    kept_on_undo: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresetRead(BaseModel):
    id: uuid.UUID | None
    name: str
    mapping: dict[str, str]
    built_in: bool


class UploadResponse(BaseModel):
    job: ImportJobRead
    sample: list[dict[str, str]]
    presets: list[PresetRead]


class CheckRequest(BaseModel):
    mapping: dict[str, str | None]
    duplicate_mode: str = "skip"
    save_preset_as: str | None = None


class RowProblem(BaseModel):
    row_number: int
    message: str


class CheckResponse(BaseModel):
    job: ImportJobRead
    valid: int
    invalid: int
    duplicates: int
    with_warnings: int
    problems: list[RowProblem]


# ------------------------------------------------------------------- routes


@router.get("/imports/catalog", response_model=ImportCatalog)
def import_catalog(_: CurrentUser = Depends(require_admin)) -> ImportCatalog:
    """What can be imported, and each field a column can be mapped to."""
    return ImportCatalog(
        entities=[
            EntityInfo(
                key=importer.key,
                label=importer.label,
                fields=[
                    FieldInfo(
                        key=f.key, label=f.label, kind=f.kind, required=f.required, help=f.help, choices=list(f.choices)
                    )
                    for f in importer.fields
                ],
            )
            for importer in IMPORTERS.values()
        ],
        limits=ImportLimits(max_file_mb=MAX_FILE_BYTES // (1024 * 1024), max_rows=MAX_ROWS, extensions=SUPPORTED_EXTENSIONS),
    )


@router.post("/imports", response_model=UploadResponse, status_code=201)
async def upload_import(
    entity: str = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> UploadResponse:
    """Upload a file. Nothing is imported yet: the rows are staged, and the
    response carries the columns, a sample and a suggested mapping."""
    data = await file.read(MAX_FILE_BYTES + 1)
    job = import_service.create_import(
        db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        entity=entity,
        file_name=file.filename or "upload",
        data=data,
    )
    return UploadResponse(
        job=ImportJobRead.model_validate(job),
        sample=import_service.sample_rows(db, job),
        presets=[PresetRead(**p) for p in import_service.list_presets(db, current_user.organization_id, job.entity)],
    )


@router.get("/imports", response_model=list[ImportJobRead])
def list_imports(
    entity: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> list[ImportJobRead]:
    query = select(ImportJob).where(ImportJob.organization_id == current_user.organization_id)
    if entity:
        query = query.where(ImportJob.entity == entity)
    jobs = db.scalars(query.order_by(ImportJob.created_at.desc()).limit(limit)).all()
    return [ImportJobRead.model_validate(j) for j in jobs]


@router.get("/imports/presets", response_model=list[PresetRead])
def list_presets(
    entity: str,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> list[PresetRead]:
    import_service.get_importer(entity)
    return [PresetRead(**p) for p in import_service.list_presets(db, current_user.organization_id, entity)]


@router.delete("/imports/presets/{preset_id}", status_code=204)
def delete_preset(
    preset_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> None:
    import_service.delete_preset(db, current_user.organization_id, preset_id)


@router.get("/imports/{job_id}", response_model=ImportJobRead)
def get_import(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> ImportJobRead:
    return ImportJobRead.model_validate(import_service.get_job(db, current_user.organization_id, job_id))


@router.post("/imports/{job_id}/check", response_model=CheckResponse)
def check_import(
    job_id: uuid.UUID,
    payload: CheckRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> CheckResponse:
    """Validate every row against the mapping; writes nothing but the verdicts."""
    job = import_service.get_job(db, current_user.organization_id, job_id)
    result = import_service.check_import(
        db,
        job,
        mapping=payload.mapping,
        duplicate_mode=payload.duplicate_mode,
        preset_name=payload.save_preset_as,
    )
    return CheckResponse(job=ImportJobRead.model_validate(job), **result)


@router.post("/imports/{job_id}/process", response_model=ImportJobRead)
def process_import(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> ImportJobRead:
    """Import the next chunk (up to 1,000 rows). Call until status is
    "completed"; calling after an interruption carries on where it stopped."""
    job = import_service.get_job(db, current_user.organization_id, job_id)
    was_checked = job.status == import_service.CHECKED
    import_service.start_import(db, job)
    job = import_service.process_next_chunk(db, current_user.organization_id, job_id)
    if was_checked or job.status == import_service.COMPLETED:
        record_audit(
            db,
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
            action=AuditAction.DATA_IMPORTED.value,
            resource_type=job.entity,
            resource_id=str(job.id),
            metadata={
                "file_name": job.file_name,
                "phase": "started" if was_checked else "completed",
                "rows": job.total_rows,
                "created": job.created_count,
                "updated": job.updated_count,
            },
        )
        db.commit()
    return ImportJobRead.model_validate(job)


@router.get("/imports/{job_id}/rejected")
def download_rejected(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    """The rows that were not imported, with the reason, as CSV."""
    job = import_service.get_job(db, current_user.organization_id, job_id)
    stem = job.file_name.rsplit(".", 1)[0]
    return StreamingResponse(
        import_service.rejected_rows_csv(db, job),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(stem)}-rejected.csv"'},
    )


@router.post("/imports/{job_id}/undo", response_model=ImportJobRead)
def undo_import(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> ImportJobRead:
    """Undo an import, a batch at a time: call until status is "undone"."""
    job = import_service.get_job(db, current_user.organization_id, job_id)
    job = import_service.undo_import(db, job)
    if job.status != import_service.UNDONE:
        return ImportJobRead.model_validate(job)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.DATA_IMPORT_UNDONE.value,
        resource_type=job.entity,
        resource_id=str(job.id),
        metadata={"file_name": job.file_name, "kept_in_use": job.kept_on_undo},
    )
    db.commit()
    return ImportJobRead.model_validate(job)


@router.get("/exports/{entity}")
def export_entity(
    entity: str,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    """Every record of one kind, as CSV or JSON, with headers an import reads back."""
    if entity not in IMPORTERS:
        raise ValidationAppError(f"Unknown export type '{entity}'.")
    count = import_service.export_count(db, current_user.organization_id, entity)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.DATA_EXPORTED.value,
        resource_type=entity,
        metadata={"format": format, "rows": count},
    )
    db.commit()
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    return StreamingResponse(
        import_service.export_rows(db, current_user.organization_id, entity, format),
        media_type="application/json" if format == "json" else "text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{entity}-{stamp}.{format}"'},
    )


def _safe_name(stem: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in stem)[:80] or "import"
