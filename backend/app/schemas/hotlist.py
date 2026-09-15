import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class HotlistCreate(BaseModel):
    name: str
    template_id: uuid.UUID | None = None
    subject: str | None = None
    body: str | None = None
    attach_spreadsheet: bool | None = None
    include_rates: bool | None = None
    include_candidate_contact: bool | None = None
    notes: str | None = None


class HotlistUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    template_id: uuid.UUID | None = None
    subject: str | None = None
    body: str | None = None
    attach_spreadsheet: bool | None = None
    include_rates: bool | None = None
    include_candidate_contact: bool | None = None
    notes: str | None = None


class HotlistMemberRead(BaseModel):
    id: uuid.UUID
    bench_profile_id: uuid.UUID
    sort_order: int
    headline_override: str | None
    # Denormalised for display so the list renders without extra lookups.
    full_name: str
    email: str
    marketing_title: str | None
    work_auth: str | None
    bench_age_days: int


class SetMembersRequest(BaseModel):
    bench_profile_ids: list[uuid.UUID]


class RecipientInput(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    company: str | None = None


class AddRecipientsRequest(BaseModel):
    recipients: list[RecipientInput]


class AddPartyRecipientsRequest(BaseModel):
    """Pull recipients from existing client or vendor records."""

    client_ids: list[uuid.UUID] | None = None
    vendor_ids: list[uuid.UUID] | None = None


class HotlistRecipientRead(BaseModel):
    id: uuid.UUID
    kind: str
    first_name: str | None
    last_name: str | None
    email: str
    company: str | None
    client_id: uuid.UUID | None
    vendor_id: uuid.UUID | None
    unsubscribed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipientImportResult(BaseModel):
    parsed: int
    added: int
    skipped: int
    # Row-level messages, so one bad row does not hide the rest.
    problems: list[str]


class HotlistDeliveryRead(BaseModel):
    id: uuid.UUID
    recipient_email: str
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HotlistSendRead(BaseModel):
    id: uuid.UUID
    status: str
    subject: str
    member_count: int
    recipient_count: int
    sent_count: int
    failed_count: int
    error_message: str | None
    completed_at: datetime | None
    sent_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HotlistRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    status: str
    template_id: uuid.UUID | None
    subject: str | None
    body: str | None
    attach_spreadsheet: bool
    include_rates: bool
    include_candidate_contact: bool
    notes: str | None
    members: list[HotlistMemberRead]
    recipients: list[HotlistRecipientRead]
    created_at: datetime
    updated_at: datetime


class HotlistListItem(BaseModel):
    """Lighter shape for the index page."""

    id: uuid.UUID
    name: str
    status: str
    subject: str | None
    member_count: int
    recipient_count: int
    created_at: datetime
    updated_at: datetime
