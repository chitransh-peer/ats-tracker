import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import JobPriority, JobStatus
from app.db.base import AuditedByMixin, Base, SoftDeleteMixin, TimestampMixin, uuid_pk


class Job(TimestampMixin, AuditedByMixin, SoftDeleteMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "req_id", name="uq_jobs_org_req_id"),
        UniqueConstraint("organization_id", "slug", name="uq_jobs_org_slug"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    req_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    hiring_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    stage_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stage_templates.id", ondelete="SET NULL"), nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace: Mapped[str] = mapped_column(String(20), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    openings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pay_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pay_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=JobPriority.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=JobStatus.DRAFT.value)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    nice_to_have: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    screening_questions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    experience: Mapped[str | None] = mapped_column(String(100), nullable=True)
    education: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Job details ---
    business_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facility: Mapped[str | None] = mapped_column(String(150), nullable=True)
    end_client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_status_detail: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    required_hours_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interview_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    clearance_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    additional_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_test_template: Mapped[str | None] = mapped_column(String(150), nullable=True)
    employment_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_documents: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    work_authorizations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Respond-by / turnaround
    respond_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    respond_by_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    turnaround_time_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnaround_time_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Rates — `pay_min`/`pay_max` above hold the candidate-facing pay range.
    pay_rate_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    pay_rate_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="Hourly")
    pay_rate_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    client_bill_rate_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    client_bill_rate_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    client_bill_rate_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    client_bill_rate_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="Hourly")
    client_bill_rate_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Address
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    states: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # --- Skills ---
    experience_min_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_max_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Organizational information ---
    max_allowed_submissions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tax_terms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    sales_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recruitment_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    account_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    primary_recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship()
    stage_template: Mapped["StageTemplate"] = relationship()
    sales_manager: Mapped["User"] = relationship(foreign_keys=[sales_manager_id])
    recruitment_manager: Mapped["User"] = relationship(foreign_keys=[recruitment_manager_id])
    account_manager: Mapped["User"] = relationship(foreign_keys=[account_manager_id])
    primary_recruiter: Mapped["User"] = relationship(foreign_keys=[primary_recruiter_id])
    created_by_user: Mapped["User"] = relationship(foreign_keys="Job.created_by")
    updated_by_user: Mapped["User"] = relationship(foreign_keys="Job.updated_by")
    notes: Mapped[list["JobNote"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    documents: Mapped[list["JobDocument"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    custom_fields: Mapped[list["JobCustomField"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    search_criteria: Mapped["JobSearchCriteria"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )


class JobNote(TimestampMixin, Base):
    __tablename__ = "job_notes"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note_type: Mapped[str] = mapped_column(String(30), nullable=False, default="Job Posting")
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["Job"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship()


class JobDocument(TimestampMixin, Base):
    __tablename__ = "job_documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    job: Mapped["Job"] = relationship(back_populates="documents")


class JobCustomField(TimestampMixin, Base):
    """A user-defined field captured against a job."""

    __tablename__ = "job_custom_fields"
    __table_args__ = (UniqueConstraint("job_id", "field_name", name="uq_job_custom_field_name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(150), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="custom_fields")


class JobSearchCriteria(TimestampMixin, Base):
    """The saved sourcing search attached to a job — the Search Criteria rail."""

    __tablename__ = "job_search_criteria"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    boolean_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recent_job_title_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    search_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="radius")
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    radius_miles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_radius_within_state: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    include_applicants_without_country: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    experience_min_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_max_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    work_authorizations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    employer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    most_recent_employer_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    willing_to_relocate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    clearance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="search_criteria")
