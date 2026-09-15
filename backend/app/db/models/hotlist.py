"""Hotlists: a curated set of bench consultants marketed to clients and vendors.

A hotlist has two sides, because bench sales needs both:

  * **Members** — the consultants on the list. Exported as an Excel sheet and
    attached to the outgoing email.
  * **Recipients** — who receives it. Built from existing client and vendor
    contacts, typed in by hand, or bulk-imported from a spreadsheet of
    first name / last name / email.

Sends are recorded per recipient so a failed address is visible rather than
silently dropped, and so "who have we already told about this consultant?" has
an answer.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import HotlistRecipientKind, HotlistSendStatus, HotlistStatus, OutboundMessageStatus
from app.db.base import AuditedByMixin, Base, TimestampMixin, uuid_pk


class Hotlist(TimestampMixin, AuditedByMixin, Base):
    __tablename__ = "hotlists"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=HotlistStatus.DRAFT.value, index=True)

    # The covering email. Either composed inline or seeded from a template.
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communication_templates.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Whether to attach the generated .xlsx. Some senders prefer the consultant
    # table inline in the email body instead.
    attach_spreadsheet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_rates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Off by default: candidate contact details are usually withheld from
    # vendors until they express interest, to stop the list being poached.
    include_candidate_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    members: Mapped[list["HotlistMember"]] = relationship(
        back_populates="hotlist", cascade="all, delete-orphan", lazy="selectin"
    )
    recipients: Mapped[list["HotlistRecipient"]] = relationship(
        back_populates="hotlist", cascade="all, delete-orphan", lazy="selectin"
    )
    sends: Mapped[list["HotlistSend"]] = relationship(
        back_populates="hotlist", cascade="all, delete-orphan", order_by="HotlistSend.created_at.desc()"
    )


class HotlistMember(Base):
    """One consultant on the list."""

    __tablename__ = "hotlist_members"
    __table_args__ = (UniqueConstraint("hotlist_id", "bench_profile_id", name="uq_hotlist_member"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    hotlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bench_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bench_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Optional per-list override, so the same consultant can be pitched
    # differently to different audiences without editing the bench profile.
    headline_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hotlist: Mapped["Hotlist"] = relationship(back_populates="members")
    bench_profile: Mapped["BenchProfile"] = relationship(lazy="selectin")


class HotlistRecipient(Base):
    """Someone who receives the hotlist.

    `email` is denormalised rather than always read through the client/vendor
    link, because an imported spreadsheet row may not correspond to any record
    in the system, and because the address used for a past send must stay
    accurate even if the contact record later changes.
    """

    __tablename__ = "hotlist_recipients"
    __table_args__ = (UniqueConstraint("hotlist_id", "email", name="uq_hotlist_recipient_email"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    hotlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default=HotlistRecipientKind.MANUAL.value)

    first_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )

    # Honoured on every send. Set when someone asks to stop receiving hotlists.
    unsubscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hotlist: Mapped["Hotlist"] = relationship(back_populates="recipients")

    @property
    def display_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) if parts else self.email


class HotlistSend(TimestampMixin, Base):
    """One dispatch of a hotlist — a batch across all its recipients."""

    __tablename__ = "hotlist_sends"

    id: Mapped[uuid.UUID] = uuid_pk()
    hotlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=HotlistSendStatus.PENDING.value)
    # Snapshotted so the audit record survives later edits to the hotlist.
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    hotlist: Mapped["Hotlist"] = relationship(back_populates="sends")
    deliveries: Mapped[list["HotlistDelivery"]] = relationship(
        back_populates="send", cascade="all, delete-orphan", lazy="selectin"
    )


class HotlistDelivery(Base):
    """Per-recipient outcome of a send, so a bad address is visible."""

    __tablename__ = "hotlist_deliveries"

    id: Mapped[uuid.UUID] = uuid_pk()
    hotlist_send_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotlist_sends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=OutboundMessageStatus.LOGGED.value)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    send: Mapped["HotlistSend"] = relationship(back_populates="deliveries")


__all__ = ["Hotlist", "HotlistMember", "HotlistRecipient", "HotlistSend", "HotlistDelivery"]
