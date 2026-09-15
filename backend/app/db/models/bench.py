"""Talent Bench: consultants available to market to clients and vendors.

A bench profile *extends* an existing candidate rather than duplicating one.
Name, email, phone, skills, work authorization and résumés already live on
`candidates`, so this table holds only what is specific to being on the bench:
availability, rate expectations, marketing ownership, and status.

That keeping-one-person-one-record choice matters: a consultant who is benched,
then placed, then benched again keeps a single history, and a résumé uploaded
during recruiting is immediately usable for bench marketing.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BenchStatus, BenchSubStatus, RateUnit, TaxTerm
from app.db.base import AuditedByMixin, Base, SoftDeleteMixin, TimestampMixin, uuid_pk


class BenchProfile(TimestampMixin, AuditedByMixin, SoftDeleteMixin, Base):
    __tablename__ = "bench_profiles"
    # One bench profile per candidate: the bench is a state a person is in, not
    # a separate record that could drift out of sync with the candidate.
    __table_args__ = (
        UniqueConstraint("candidate_id", name="uq_bench_profile_candidate"),
        UniqueConstraint("organization_id", "bench_code", name="uq_bench_profile_org_code"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Short human-readable handle, sequential per organization (the "Bench ID"
    # recruiters quote to each other).
    bench_code: Mapped[int] = mapped_column(Integer, nullable=False)

    marketing_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=BenchStatus.ACTIVE.value, index=True)
    sub_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Bench age is derived from this rather than stored, so it can never go stale.
    bench_start_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Rate expectations, e.g. "USD 30 Hourly C2C" from the bench list.
    desired_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    rate_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    rate_unit: Mapped[str | None] = mapped_column(String(20), nullable=True, default=RateUnit.HOURLY.value)
    tax_term: Mapped[str | None] = mapped_column(String(20), nullable=True, default=TaxTerm.C2C.value)

    # Marketing ownership. These drive who can see the profile (see the bench
    # service's scoping rules) as well as who is accountable for it.
    sales_team_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    account_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    preferred_locations: Mapped[str | None] = mapped_column(String(500), nullable=True)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    marketing_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Kept off hotlist exports by default — an internal-only note.
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate: Mapped["Candidate"] = relationship()
    owners: Mapped[list["BenchProfileOwner"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    submissions: Mapped[list["BenchSubmission"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="BenchSubmission.created_at.desc()"
    )

    @property
    def bench_age_days(self) -> int:
        """Days since the consultant went on the bench."""
        return (date.today() - self.bench_start_date).days


class BenchProfileOwner(Base):
    """Additional owners beyond the sales member and account manager.

    A separate table because the bench list shows several owners per consultant
    ("Sandeep Bisane, Seema Mittal") and ownership drives visibility.
    """

    __tablename__ = "bench_profile_owners"
    __table_args__ = (UniqueConstraint("bench_profile_id", "user_id", name="uq_bench_owner"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    bench_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bench_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile: Mapped["BenchProfile"] = relationship(back_populates="owners")


class BenchSubmission(TimestampMixin, Base):
    """A record of marketing this consultant to a client or vendor.

    Answers "who have we already sent this person to?", which prevents the
    classic double-submission problem in bench sales.
    """

    __tablename__ = "bench_submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    bench_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bench_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    submitted_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    profile: Mapped["BenchProfile"] = relationship(back_populates="submissions")


# Re-exported for the models package.
__all__ = ["BenchProfile", "BenchProfileOwner", "BenchSubmission", "BenchStatus", "BenchSubStatus"]
