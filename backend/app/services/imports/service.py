"""Running an import: upload -> check -> import in chunks -> report / undo.

Nothing here holds a whole file in one transaction or one request. The file is
staged into `import_rows` on upload; the check reads those rows in batches; the
import itself advances one chunk per call (`process_next_chunk`), committing as
it goes. So a 100,000-row import is a hundred short requests, any of which can
fail or be interrupted without losing the others, and calling again resumes
exactly where it stopped.
"""

import csv
import io
import json
import logging
import time
import uuid
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import bindparam, delete, func, insert, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.db.models.import_job import ImportJob, ImportPreset, ImportRow
from app.services.imports.entities import BUILT_IN_PRESETS, IMPORTERS, ImportContext, Importer, RowValues
from app.services.imports.fields import FieldError, convert, is_unknown_choice, normalize_header
from app.services.imports.parsing import parse_file

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
_STAGE_BATCH = 5000

# Job status
UPLOADED = "uploaded"
CHECKED = "checked"
IMPORTING = "importing"
COMPLETED = "completed"
UNDOING = "undoing"
UNDONE = "undone"

# Row status
PENDING = "pending"
VALID = "valid"
INVALID = "invalid"
DUPLICATE = "duplicate"
CREATED = "created"
UPDATED = "updated"
SKIPPED = "skipped"
REJECTED = "rejected"

DUPLICATE_MODES = ("skip", "update")


def get_importer(entity: str) -> Importer:
    importer = IMPORTERS.get(entity)
    if importer is None:
        raise ValidationAppError(f"Unknown import type '{entity}'. Use one of: {', '.join(IMPORTERS)}.")
    return importer


def get_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
    job = db.scalar(select(ImportJob).where(ImportJob.id == job_id, ImportJob.organization_id == organization_id))
    if job is None:
        raise NotFoundError("Import not found")
    return job


# ------------------------------------------------------------------ mapping


def suggest_mapping(importer: Importer, columns: list[str], presets: list[dict] | None = None) -> dict[str, str | None]:
    """Guess which field each column is. A saved or built-in preset whose
    columns all appear in the file wins outright; otherwise each column is
    matched by name against the fields and their common aliases."""
    for preset in presets or []:
        if preset["mapping"] and set(preset["mapping"]) <= set(columns):
            return {c: preset["mapping"].get(c) for c in columns}

    mapping: dict[str, str | None] = {}
    taken: set[str] = set()
    for column in columns:
        name = normalize_header(column)
        match = next((f for f in importer.fields if name in f.names), None)
        # One column per field, except the note, which collects many.
        if match and (match.key not in taken or match.kind == "note"):
            mapping[column] = match.key
            taken.add(match.key)
        else:
            mapping[column] = None
    return mapping


def list_presets(db: Session, organization_id: uuid.UUID, entity: str) -> list[dict]:
    saved = db.scalars(
        select(ImportPreset)
        .where(ImportPreset.organization_id == organization_id, ImportPreset.entity == entity)
        .order_by(ImportPreset.name)
    ).all()
    built_in = [
        {"id": None, "name": name, "mapping": mapping, "built_in": True}
        for name, mapping in BUILT_IN_PRESETS.get(entity, {}).items()
    ]
    return built_in + [{"id": p.id, "name": p.name, "mapping": p.mapping, "built_in": False} for p in saved]


def save_preset(db: Session, organization_id: uuid.UUID, entity: str, name: str, mapping: dict) -> ImportPreset:
    name = name.strip()[:100]
    if not name:
        raise ValidationAppError("Give the saved mapping a name.")
    preset = db.scalar(
        select(ImportPreset).where(
            ImportPreset.organization_id == organization_id, ImportPreset.entity == entity, ImportPreset.name == name
        )
    )
    if preset is None:
        preset = ImportPreset(organization_id=organization_id, entity=entity, name=name)
        db.add(preset)
    preset.mapping = {column: target for column, target in mapping.items() if target}
    db.flush()
    return preset


def delete_preset(db: Session, organization_id: uuid.UUID, preset_id: uuid.UUID) -> None:
    preset = db.scalar(
        select(ImportPreset).where(ImportPreset.id == preset_id, ImportPreset.organization_id == organization_id)
    )
    if preset is None:
        raise NotFoundError("Saved mapping not found")
    db.delete(preset)
    db.commit()


# ------------------------------------------------------------------- upload


def create_import(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    entity: str,
    file_name: str,
    data: bytes,
) -> ImportJob:
    importer = get_importer(entity)
    columns, rows = parse_file(data, file_name)

    job = ImportJob(
        organization_id=organization_id,
        entity=importer.key,
        status=UPLOADED,
        file_name=file_name[:255],
        columns=columns,
        mapping={},
        duplicate_mode="skip",
        total_rows=len(rows),
        processed_rows=0,
        created_count=0,
        updated_count=0,
        skipped_count=0,
        rejected_count=0,
        kept_on_undo=0,
        created_by=actor_id,
    )
    db.add(job)
    db.flush()

    job.mapping = suggest_mapping(importer, columns, list_presets(db, organization_id, importer.key))

    for start in range(0, len(rows), _STAGE_BATCH):
        db.execute(
            insert(ImportRow),
            [
                {"import_job_id": job.id, "row_number": start + i + 1, "data": row, "status": PENDING}
                for i, row in enumerate(rows[start : start + _STAGE_BATCH])
            ],
        )
    db.commit()
    db.refresh(job)
    return job


def sample_rows(db: Session, job: ImportJob, limit: int = 5) -> list[dict]:
    return list(
        db.scalars(
            select(ImportRow.data).where(ImportRow.import_job_id == job.id).order_by(ImportRow.row_number).limit(limit)
        ).all()
    )


# -------------------------------------------------------------- conversion


def _convert_row(importer: Importer, mapping: dict[str, str], raw: dict[str, str]) -> tuple[RowValues, list[str]]:
    """A staged row's raw text as typed field values; plus any errors."""
    row = RowValues()
    errors: list[str] = []
    fields = {f.key: f for f in importer.fields}

    for column, target in mapping.items():
        f = fields.get(target) if target else None
        if f is None:
            continue
        raw_value = raw.get(column)
        if f.kind == "note":
            if raw_value and raw_value.strip():
                row.notes.append(f"{column}: {raw_value.strip()}")
            continue
        if row.values.get(f.key) is not None:
            # Two columns mapped to one field (e.g. "Created On" and "Created
            # date"): the first non-empty one wins.
            continue
        try:
            value = convert(f, raw_value)
        except FieldError as exc:
            errors.append(str(exc))
            continue
        if is_unknown_choice(value):
            row.warnings.append(f"{f.label} '{value.raw}' is not one this system uses; set to {value.fallback}.")
            value = value.fallback
        row.values[f.key] = value

    # Required fields that were never mapped at all.
    for f in importer.fields:
        if f.required and row.values.get(f.key) is None and not any(e.startswith(f.label) for e in errors):
            errors.append(f"{f.label} is required.")

    if not errors:
        problem = importer.prepare(row)
        if problem:
            errors.append(problem)
    return row, errors


def _validate_mapping(importer: Importer, columns: list[str], mapping: dict) -> dict[str, str]:
    field_keys = {f.key: f for f in importer.fields}
    clean: dict[str, str] = {}
    used: dict[str, str] = {}
    for column, target in (mapping or {}).items():
        if not target:
            continue
        if column not in columns:
            raise ValidationAppError(f"The file has no column '{column}'.")
        f = field_keys.get(target)
        if f is None:
            raise ValidationAppError(f"'{target}' is not a field of {importer.label.lower()}.")
        if target in used and f.kind not in ("note", "datetime", "date"):
            raise ValidationAppError(f"Both '{used[target]}' and '{column}' are mapped to {f.label}. Pick one.")
        used.setdefault(target, column)
        clean[column] = target
    for f in importer.fields:
        if f.required and f.key not in used:
            raise ValidationAppError(f"Map a column to {f.label}; it is required.")
    return clean


# -------------------------------------------------------------------- check


def _iter_rows(db: Session, job: ImportJob, statuses: tuple[str, ...] | None = None) -> Iterator[list[ImportRow]]:
    """The job's staged rows in row order, a batch at a time, by keyset so
    each batch is one indexed range query however far into the file it is."""
    last = 0
    while True:
        query = select(ImportRow).where(ImportRow.import_job_id == job.id, ImportRow.row_number > last)
        if statuses:
            query = query.where(ImportRow.status.in_(statuses))
        batch = list(db.scalars(query.order_by(ImportRow.row_number).limit(CHUNK_SIZE)).all())
        if not batch:
            return
        yield batch
        last = batch[-1].row_number


def check_import(
    db: Session,
    job: ImportJob,
    *,
    mapping: dict,
    duplicate_mode: str,
    preset_name: str | None = None,
) -> dict:
    """Check every row against the mapping before anything is written.

    Marks each staged row valid, invalid (with the reason) or duplicate (of an
    existing record, or of an earlier row in the same file), and returns the
    counts plus the first problems to show. Re-runnable: fixing the mapping and
    checking again starts from scratch.
    """
    if job.status not in (UPLOADED, CHECKED):
        raise ConflictError("This import has already started, so its mapping can no longer change.")
    if duplicate_mode not in DUPLICATE_MODES:
        raise ValidationAppError("Duplicates must be either skipped or used to update the existing record.")

    importer = get_importer(job.entity)
    clean = _validate_mapping(importer, job.columns, mapping)
    job.mapping = clean
    job.duplicate_mode = duplicate_mode
    if preset_name:
        save_preset(db, job.organization_id, job.entity, preset_name, clean)

    ctx = ImportContext(job.organization_id, job.created_by, job.id, job.file_name)
    seen: dict[tuple[str, str], int] = {}
    counts = {VALID: 0, INVALID: 0, DUPLICATE: 0}
    problems: list[dict] = []
    warnings = 0

    # Core, not ORM, update: one executemany of (row_id, status, message) per
    # batch, without the ORM's per-object bookkeeping.
    rows_table = ImportRow.__table__
    update_rows = (
        update(rows_table)
        .where(rows_table.c.id == bindparam("row_id"))
        .values(status=bindparam("new_status"), message=bindparam("new_message"))
    )
    for batch in _iter_rows(db, job):
        converted = [_convert_row(importer, clean, r.data) for r in batch]
        resolvable = [i for i, (_, errors) in enumerate(converted) if not errors]
        resolve_errors = importer.resolve(db, ctx, [converted[i][0] for i in resolvable])
        for i, error in zip(resolvable, resolve_errors, strict=True):
            if error:
                converted[i][1].append(error)

        clean_rows = [i for i, (_, errors) in enumerate(converted) if not errors]
        existing = (
            importer.find_existing(db, ctx, [converted[i][0] for i in clean_rows]) if importer.matches_existing else []
        )
        existing_by_index = dict(zip(clean_rows, existing, strict=False))

        changes = []
        for i, staged in enumerate(batch):
            values, errors = converted[i]
            if errors:
                status, message = INVALID, " ".join(errors)
            elif existing_by_index.get(i):
                status, message = DUPLICATE, "Matches a record already in the system."
            else:
                keys = importer.match_keys(values)
                earlier = next((seen[k] for k in keys if k in seen), None)
                if earlier:
                    status, message = DUPLICATE, f"Same record as row {earlier} of this file."
                else:
                    status, message = VALID, None
                    for k in keys:
                        seen.setdefault(k, staged.row_number)
            if values.warnings and status != INVALID:
                warnings += 1
                message = " ".join(filter(None, [message, *values.warnings]))
            counts[status] += 1
            if status == INVALID and len(problems) < 50:
                problems.append({"row_number": staged.row_number, "message": message})
            changes.append({"row_id": staged.id, "new_status": status, "new_message": message})
        db.execute(update_rows, changes)

    job.status = CHECKED
    job.rejected_count = counts[INVALID]
    db.commit()
    db.refresh(job)
    return {
        "valid": counts[VALID],
        "invalid": counts[INVALID],
        "duplicates": counts[DUPLICATE],
        "with_warnings": warnings,
        "problems": problems,
    }


# ------------------------------------------------------------------ process


def start_import(db: Session, job: ImportJob) -> ImportJob:
    if job.status == CHECKED:
        job.status = IMPORTING
        # Rows the check rejected are final; mark them so the report shows them.
        db.execute(
            update(ImportRow)
            .where(ImportRow.import_job_id == job.id, ImportRow.status == INVALID)
            .values(status=REJECTED)
            .execution_options(synchronize_session=False)
        )
        job.processed_rows = job.rejected_count
        db.commit()
    elif job.status not in (IMPORTING, COMPLETED):
        raise ConflictError("Check the file before importing it.")
    return job


def process_next_chunk(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
    """Import the next chunk of rows and return the job with its progress.

    Safe to call from two tabs at once: the job row is locked for the chunk,
    and a caller that finds it locked simply gets the progress back.
    """
    try:
        job = db.scalar(
            select(ImportJob)
            .where(ImportJob.id == job_id, ImportJob.organization_id == organization_id)
            .with_for_update(nowait=True)
        )
    except OperationalError:
        db.rollback()
        return get_job(db, organization_id, job_id)
    if job is None:
        raise NotFoundError("Import not found")
    if job.status != IMPORTING:
        db.rollback()
        return job

    importer = get_importer(job.entity)
    rows = list(
        db.scalars(
            select(ImportRow)
            .where(ImportRow.import_job_id == job.id, ImportRow.status.in_((VALID, DUPLICATE)))
            .order_by(ImportRow.row_number)
            .limit(CHUNK_SIZE)
        ).all()
    )
    if not rows:
        job.status = COMPLETED
        db.commit()
        return job

    ctx = ImportContext(job.organization_id, job.created_by, job.id, job.file_name)
    try:
        _import_rows(db, importer, ctx, job, rows)
        db.commit()
    except Exception:
        # One bad row must not sink the chunk: redo it a row at a time, each in
        # its own savepoint, and reject only the rows that actually fail.
        db.rollback()
        logger.exception("Import %s chunk failed; retrying row by row", job.id)
        job = db.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        rows = list(db.scalars(select(ImportRow).where(ImportRow.id.in_([r.id for r in rows]))).all())
        for row in rows:
            savepoint = db.begin_nested()
            try:
                _import_rows(db, importer, ctx, job, [row])
                savepoint.commit()
            except Exception as exc:
                savepoint.rollback()
                row.status = REJECTED
                row.message = f"Could not be saved: {str(exc).splitlines()[0][:300]}"
                job.rejected_count += 1
                job.processed_rows += 1
        db.commit()

    db.refresh(job)
    return job


def _import_rows(db: Session, importer: Importer, ctx: ImportContext, job: ImportJob, rows: list[ImportRow]) -> None:
    converted = []
    for staged in rows:
        values, errors = _convert_row(importer, job.mapping, staged.data)
        converted.append((staged, values, errors))

    ok = [(s, v) for s, v, e in converted if not e]
    resolve_errors = importer.resolve(db, ctx, [v for _, v in ok])
    for (staged, _), error in zip(ok, resolve_errors, strict=True):
        if error:
            staged.status, staged.message = REJECTED, error
    for staged, _, errors in converted:
        if errors:
            staged.status, staged.message = REJECTED, " ".join(errors)

    ready = [(s, v) for s, v in ok if s.status not in (REJECTED,)]
    # Matched again now rather than trusting the check: earlier chunks of this
    # same import may have created the record a later row duplicates.
    existing = importer.find_existing(db, ctx, [v for _, v in ready]) if importer.matches_existing else [None] * len(ready)

    to_create: list[tuple[ImportRow, RowValues]] = []
    # Rows in this same chunk that are the same record as an earlier row: the
    # database cannot catch those, since neither exists there yet.
    first_in_chunk: dict[tuple[str, str], ImportRow] = {}
    same_as: list[tuple[ImportRow, ImportRow]] = []
    for (staged, values), existing_id in zip(ready, existing, strict=True):
        if existing_id is None:
            keys = importer.match_keys(values)
            earlier = next((first_in_chunk[k] for k in keys if k in first_in_chunk), None)
            if earlier is not None:
                same_as.append((staged, earlier))
                continue
            for k in keys:
                first_in_chunk.setdefault(k, staged)
            to_create.append((staged, values))
        elif job.duplicate_mode == "update":
            importer.update(db, ctx, existing_id, values)
            staged.status, staged.record_id = UPDATED, existing_id
            staged.message = "Updated the existing record."
        else:
            staged.status, staged.record_id = SKIPPED, existing_id
            staged.message = "Skipped: matches a record already in the system."

    if to_create:
        ids = importer.create_many(db, ctx, [v for _, v in to_create])
        for (staged, values), record_id in zip(to_create, ids, strict=True):
            staged.status, staged.record_id = CREATED, record_id
            staged.message = " ".join(values.warnings) or None
    for staged, earlier in same_as:
        staged.status, staged.record_id = SKIPPED, earlier.record_id
        staged.message = f"Skipped: same record as row {earlier.row_number} of this file."

    job.processed_rows += len(rows)
    job.created_count += sum(1 for r in rows if r.status == CREATED)
    job.updated_count += sum(1 for r in rows if r.status == UPDATED)
    job.skipped_count += sum(1 for r in rows if r.status == SKIPPED)
    job.rejected_count += sum(1 for r in rows if r.status == REJECTED)
    db.flush()


# ------------------------------------------------------------------- report


def rejected_rows_csv(db: Session, job: ImportJob) -> Iterator[str]:
    """The rows that did not go in, in the file's own columns, with the reason
    first, so they can be fixed in a spreadsheet and imported again."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        value = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return value

    writer.writerow(["Row", "Problem", *job.columns])
    yield "﻿" + flush()  # BOM, so Excel opens it as UTF-8
    for batch in _iter_rows(db, job, (REJECTED, INVALID)):
        for row in batch:
            writer.writerow([row.row_number, row.message or "", *[row.data.get(c, "") for c in job.columns]])
        yield flush()


# --------------------------------------------------------------------- undo


def undo_import(db: Session, job: ImportJob, *, time_budget_seconds: float = 30.0) -> ImportJob:
    """Delete what this import created, except records something now depends
    on (a candidate who has since applied to a job, a client with jobs...).
    Records it updated keep their new values: there is nothing to go back to.

    Works for at most `time_budget_seconds` per call and returns the job with
    status "undoing" if there is more to do, so undoing 100,000 records is a
    few short requests rather than one that outlives the request timeout.
    Deletes in bulk; child rows (tags, notes, contacts...) go with their parent
    through the database's ON DELETE CASCADE.
    """
    if job.status not in (COMPLETED, IMPORTING, UNDOING):
        raise ConflictError("Only an import that has run can be undone.")
    job.status = UNDOING
    db.commit()

    importer = get_importer(job.entity)
    model = importer.model
    table = model.__table__
    started = time.monotonic()

    while time.monotonic() - started < time_budget_seconds:
        ids = list(
            db.scalars(
                select(model.id)
                .where(model.organization_id == job.organization_id, model.import_job_id == job.id)
                .limit(CHUNK_SIZE)
            ).all()
        )
        if not ids:
            job.status = UNDONE
            break
        protected = importer.in_use(db, ids)
        removable = [i for i in ids if i not in protected]
        if removable:
            db.execute(delete(table).where(table.c.id.in_(removable)))
        if protected:
            # Unlinked from the import so the next pass does not find them again.
            db.execute(update(table).where(table.c.id.in_(protected)).values(import_job_id=None))
            job.kept_on_undo += len(protected)
        db.commit()

    db.commit()
    db.refresh(job)
    return job


# ------------------------------------------------------------------- export


def _export_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


def _export_headers(importer: Importer) -> list[tuple[str, str]]:
    labels = {f.key: f.label for f in importer.fields}
    extra = {"req_id": "Req ID", "status": "Status", "created_at": "Created on", "location": "Location"}
    return [(key, labels.get(key) or extra.get(key) or key.replace("_", " ").title()) for key in importer.export_fields]


def export_count(db: Session, organization_id: uuid.UUID, entity: str) -> int:
    importer = get_importer(entity)
    query = importer.export_query(organization_id)
    return db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0


def export_rows(db: Session, organization_id: uuid.UUID, entity: str, fmt: str) -> Iterator[str]:
    """Every record of `entity`, streamed as CSV or JSON. The column headers
    are the import field labels, so an exported file imports straight back."""
    importer = get_importer(entity)
    headers = _export_headers(importer)
    query = importer.export_query(organization_id).execution_options(yield_per=CHUNK_SIZE)

    if fmt == "json":
        yield "["
        first = True
        for obj in db.scalars(query):
            record = {label: _export_text(importer.export_value(obj, key)) or None for key, label in headers}
            yield ("" if first else ",") + "\n" + json.dumps(record, ensure_ascii=False)
            first = False
        yield "\n]\n"
        return

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        value = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return value

    writer.writerow([label for _, label in headers])
    yield "﻿" + flush()  # BOM, so Excel opens it as UTF-8
    for index, obj in enumerate(db.scalars(query), start=1):
        writer.writerow([_export_text(importer.export_value(obj, key)) for key, _ in headers])
        if index % CHUNK_SIZE == 0:
            yield flush()
    yield flush()
