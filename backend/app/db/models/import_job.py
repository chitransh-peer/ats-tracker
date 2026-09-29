import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class ImportJob(TimestampMixin, Base):
    """One uploaded file being brought into one entity (candidates, vendors...).

    The file's rows are copied into `import_rows` on upload, so every later
    step -- checking, importing in chunks, reporting, undo -- works from the
    database rather than re-reading and re-parsing the file each time.
    """

    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The file's column headers, in file order.
    columns: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    # {source column: target field key}. Several columns may feed "note".
    mapping: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # What to do with a row that matches an existing record: "skip" or "update".
    duplicate_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="skip")

    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Records an undo left in place because something now depends on them.
    kept_on_undo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportRow(Base):
    """One row of an uploaded file, and what became of it."""

    __tablename__ = "import_rows"
    __table_args__ = (Index("ix_import_rows_job_status_row", "import_job_id", "status", "row_number"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    # 1-based, counting data rows only, so it matches what a spreadsheet user
    # sees once the header row is set aside.
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # The row as it came in: {source column: raw value}.
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ImportPreset(TimestampMixin, Base):
    """A saved column mapping, e.g. "Ceipal applicants", reusable next time."""

    __tablename__ = "import_presets"
    __table_args__ = (UniqueConstraint("organization_id", "entity", "name", name="uq_import_presets_org_entity_name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mapping: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
