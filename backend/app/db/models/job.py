import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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

    client: Mapped["Client"] = relationship()
    stage_template: Mapped["StageTemplate"] = relationship()
