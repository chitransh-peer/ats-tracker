import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AIEvaluationStatus, ResumeParseStatus
from app.db.base import Base, TimestampMixin, uuid_pk


class ResumeParseRun(Base):
    __tablename__ = "resume_parse_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ResumeParseStatus.PENDING.value)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parsed_resume: Mapped["ParsedResume"] = relationship(back_populates="parse_run", uselist=False)


class ParsedResume(Base):
    __tablename__ = "parsed_resumes"

    id: Mapped[uuid.UUID] = uuid_pk()
    resume_parse_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_parse_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_experience_years: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    education: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    work_history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    parse_run: Mapped["ResumeParseRun"] = relationship(back_populates="parsed_resume")


class AIEvaluation(TimestampMixin, Base):
    __tablename__ = "ai_evaluations"
    __table_args__ = (UniqueConstraint("application_id", "version", name="uq_ai_evaluation_application_version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AIEvaluationStatus.PENDING.value)
    rule_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    recommendation_label: Mapped[str | None] = mapped_column(String(30), nullable=True)
    strengths: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    gaps: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    matched_skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    suggested_interview_questions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    explanation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    application: Mapped["Application"] = relationship()
    overrides: Mapped[list["AIEvaluationOverride"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", order_by="AIEvaluationOverride.created_at"
    )


class AIEvaluationOverride(Base):
    __tablename__ = "ai_evaluation_overrides"

    id: Mapped[uuid.UUID] = uuid_pk()
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_recommendation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_recommendation: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation: Mapped["AIEvaluation"] = relationship(back_populates="overrides")
