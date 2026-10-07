import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk


class CeipalImport(TimestampMixin, Base):
    """One Ceipal "applicants" backup being brought in.

    A backup is two kinds of ZIP: one of CSV tables (Applicants, documents
    index, education, submissions, users...) and one or more holding the
    résumé files themselves. The browser reads the ZIPs -- they run to
    gigabytes, far past what one request can carry -- and sends the tables
    as row batches and the résumés a few files at a time. So every step
    below is a short request that can fail or be repeated without loss.

    Steps: staging (rows arrive) -> importing (candidates are created a chunk
    at a time) -> documents (résumé files are matched and attached, from as
    many ZIP parts as it takes) -> completed. Undo walks it back.
    """

    __tablename__ = "ceipal_imports"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # The backup's name as uploaded, e.g. "1791306305_CEIPAL_backup_08_2026".
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    applicants_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applicants_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_expected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_attached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Listed in the documents index for an applicant who is not in this backup.
    documents_orphaned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    education_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submissions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Submissions whose Ceipal job matched one of ours, and became applications.
    submissions_linked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kept_on_undo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class CeipalRow(Base):
    """One row of one table of a backup, staged until the import runs.

    `ref` is the Ceipal applicant the row belongs to (its `Applicants.Id`;
    every child table links on that, never on "Applicant Id"). `key` is what
    the row is looked up by besides: a document's stored file name, a
    submission's id, a user's id, a degree's id.
    """

    __tablename__ = "ceipal_rows"
    __table_args__ = (
        UniqueConstraint("import_id", "kind", "source", "row_number", name="uq_ceipal_rows_position"),
        Index("ix_ceipal_rows_import_kind_ref", "import_id", "kind", "ref"),
        Index("ix_ceipal_rows_import_kind_key", "import_id", "kind", "key"),
        Index("ix_ceipal_rows_import_kind_status", "import_id", "kind", "status", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    import_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ceipal_imports.id", ondelete="CASCADE"), nullable=False
    )
    # Which table: applicants, documents, education, submissions, ...
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    # The file the row came from (a backup may arrive in several parts) and
    # its position there, so a batch sent twice is staged once.
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # What the row became: a candidate, a document, an application.
    record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CeipalProfile(TimestampMixin, Base):
    """A candidate's record as Ceipal holds it.

    `fields` keeps every Applicants column under its Ceipal header, exactly,
    so the Ceipal view of the candidate list shows what Ceipal showed. SSN
    and date of birth are never stored.
    """

    __tablename__ = "ceipal_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "ceipal_id", name="uq_ceipal_profiles_org_ceipal_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Applicants.Id in Ceipal.
    ceipal_id: Mapped[str] = mapped_column(String(100), nullable=False)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # [{submission_id, job_code, job_id, status, submitted_by, submitted_on, ...}]
    submissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    resume_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_documents.id", ondelete="SET NULL"), nullable=True
    )
    # The import that brought this profile in, and whether that import also
    # created the candidate (rather than finding one already here), which is
    # what undo needs to know.
    created_import_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ceipal_imports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_import_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ceipal_imports.id", ondelete="SET NULL"), nullable=True
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="ceipal_profile")  # noqa: F821
    resume_document: Mapped["CandidateDocument | None"] = relationship()  # noqa: F821
