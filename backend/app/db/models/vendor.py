import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ClientVisibility, VendorStatus
from app.db.base import AuditedByMixin, Base, TimestampMixin, uuid_pk


class Vendor(TimestampMixin, AuditedByMixin, Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- Business information ---
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=VendorStatus.ACTIVE.value)
    federal_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vendor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vendor_classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(50), nullable=True)
    about_vendor: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Address
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Ownership / visibility
    primary_business_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_units: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    vendor_visibility: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ClientVisibility.ORGANIZATION_LEVEL.value
    )
    primary_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ownership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    vendor_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Flags
    send_requirement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    send_hotlist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    primary_vendor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_access_to_all_users: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Lists
    technologies: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    submission_format_fields: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    submission_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    contacts: Mapped[list["VendorContact"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    accounts: Mapped[list["VendorAccount"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    notes: Mapped[list["VendorNote"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    documents: Mapped[list["VendorDocument"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    meetings: Mapped[list["VendorMeeting"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    bank_accounts: Mapped[list["VendorBankAccount"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    primary_owner: Mapped["User"] = relationship(foreign_keys=[primary_owner_id])
    ownership: Mapped["User"] = relationship(foreign_keys=[ownership_id])
    vendor_lead: Mapped["User"] = relationship(foreign_keys=[vendor_lead_id])
    created_by_user: Mapped["User"] = relationship(foreign_keys="Vendor.created_by")
    updated_by_user: Mapped["User"] = relationship(foreign_keys="Vendor.updated_by")


class VendorContact(TimestampMixin, Base):
    __tablename__ = "vendor_contacts"

    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    work_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")
    vms_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Not Initiated")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="contacts")
    owner: Mapped["User"] = relationship()


class VendorAccount(TimestampMixin, Base):
    """An account-management contact — the 'Accounts' grid on the vendor snapshot."""

    __tablename__ = "vendor_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    email_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    office_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    vendor: Mapped["Vendor"] = relationship(back_populates="accounts")


class VendorNote(TimestampMixin, Base):
    __tablename__ = "vendor_notes"

    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notified_user_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)

    vendor: Mapped["Vendor"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship()


class VendorDocument(TimestampMixin, Base):
    __tablename__ = "vendor_documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="documents")


class VendorMeeting(TimestampMixin, Base):
    __tablename__ = "vendor_meetings"

    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meeting_for: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendor_contacts.id", ondelete="SET NULL"), nullable=True
    )
    attendee_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    guest_attendees: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="meetings")
    contact: Mapped["VendorContact"] = relationship()
    creator: Mapped["User"] = relationship()


class VendorBankAccount(TimestampMixin, Base):
    __tablename__ = "vendor_bank_accounts"
    __table_args__ = (UniqueConstraint("vendor_id", "account_number", name="uq_vendor_bank_account_number"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    routing_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    swift_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    branch_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="bank_accounts")
