import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ClientStatus, ClientVisibility
from app.db.base import AuditedByMixin, Base, TimestampMixin, uuid_pk


class Client(TimestampMixin, AuditedByMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("organization_id", "client_code", name="uq_clients_org_client_code"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # --- Business information ---
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vms_client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    federal_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ClientStatus.ACTIVE.value)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    practice: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(50), nullable=True)
    about_company: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Address
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Ownership / visibility
    primary_business_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_visibility: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ClientVisibility.ORGANIZATION_LEVEL.value
    )
    primary_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ownership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    client_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parent_client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )

    # Flags
    display_on_job_posting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    send_requirement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    send_hotlist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_access_to_all_users: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notify_near_client_location: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stop_contact_email_on_submit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_address_for_jobs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Lists
    client_facilities: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    required_documents: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    submission_format_fields: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Guidelines / markup
    guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
    markup_percentage: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    overtime_markup_percentage: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    standard_working_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submission_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    contacts: Mapped[list["ClientContact"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    accounts: Mapped[list["ClientAccount"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    notes: Mapped[list["ClientNote"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    documents: Mapped[list["ClientDocument"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    assignments: Mapped[list["ClientAssignment"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    child_clients: Mapped[list["Client"]] = relationship(
        back_populates="parent_client", remote_side=None, foreign_keys=[parent_client_id]
    )
    parent_client: Mapped["Client"] = relationship(
        back_populates="child_clients", remote_side=[id], foreign_keys=[parent_client_id]
    )
    primary_owner: Mapped["User"] = relationship(foreign_keys=[primary_owner_id])
    ownership: Mapped["User"] = relationship(foreign_keys=[ownership_id])
    client_lead: Mapped["User"] = relationship(foreign_keys=[client_lead_id])
    created_by_user: Mapped["User"] = relationship(foreign_keys="Client.created_by")
    updated_by_user: Mapped["User"] = relationship(foreign_keys="Client.updated_by")


class ClientContact(TimestampMixin, Base):
    __tablename__ = "client_contacts"

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")

    client: Mapped["Client"] = relationship(back_populates="contacts")


class ClientAccount(TimestampMixin, Base):
    """An account-management contact — the 'Accounts' grid on the client snapshot."""

    __tablename__ = "client_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    email_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    office_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="accounts")


class ClientNote(TimestampMixin, Base):
    __tablename__ = "client_notes"

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note_type: Mapped[str] = mapped_column(String(30), nullable=False, default="Client")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Normal")
    body: Mapped[str] = mapped_column(Text, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship()


class ClientDocument(TimestampMixin, Base):
    __tablename__ = "client_documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    client: Mapped["Client"] = relationship(back_populates="documents")


class ClientAssignment(TimestampMixin, Base):
    """A user assigned to work this client, with the role they play on the account."""

    __tablename__ = "client_assignments"
    __table_args__ = (UniqueConstraint("client_id", "user_id", name="uq_client_assignment_user"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_role: Mapped[str | None] = mapped_column(String(100), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship()
