import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OfferApprovalStatus, OfferPayType, OfferStatus
from app.db.base import AuditedByMixin, Base, TimestampMixin, uuid_pk


class Offer(TimestampMixin, AuditedByMixin, Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=OfferStatus.DRAFT.value)
    # A salaried offer carries an annual base salary; an hourly one (W-2
    # hourly, 1099 and C2C contracts) carries an hourly rate instead.
    pay_type: Mapped[str] = mapped_column(String(10), nullable=False, default=OfferPayType.SALARY.value)
    base_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tax_term: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contract_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    application: Mapped["Application"] = relationship()
    versions: Mapped[list["OfferVersion"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan", order_by="OfferVersion.version_number"
    )
    approvals: Mapped[list["OfferApproval"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan", order_by="OfferApproval.created_at"
    )


class OfferVersion(Base):
    __tablename__ = "offer_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pay_type: Mapped[str] = mapped_column(String(10), nullable=False, default=OfferPayType.SALARY.value)
    base_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tax_term: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contract_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    offer: Mapped["Offer"] = relationship(back_populates="versions")


class OfferApproval(Base):
    __tablename__ = "offer_approvals"

    id: Mapped[uuid.UUID] = uuid_pk()
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=OfferApprovalStatus.PENDING.value)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    offer: Mapped["Offer"] = relationship(back_populates="approvals")
