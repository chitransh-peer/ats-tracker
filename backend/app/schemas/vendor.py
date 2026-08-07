import uuid
from datetime import date, datetime

from pydantic import BaseModel


class VendorContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    work_phone: str | None = None
    designation: str | None = None
    status: str = "Active"
    vms_status: str = "Not Initiated"
    owner_id: uuid.UUID | None = None


class VendorContactRead(VendorContactCreate):
    id: uuid.UUID
    owner_name: str | None = None

    model_config = {"from_attributes": True}


class VendorAccountCreate(BaseModel):
    contact_person: str
    email_id: str | None = None
    designation: str | None = None
    office_number: str | None = None
    mobile_number: str | None = None


class VendorAccountRead(VendorAccountCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class VendorNoteCreate(BaseModel):
    body: str
    action: str | None = None
    notified_user_ids: list[uuid.UUID] = []


class VendorNoteRead(BaseModel):
    id: uuid.UUID
    body: str
    action: str | None
    author_id: uuid.UUID | None
    author_name: str | None = None
    notified_user_ids: list[uuid.UUID]
    notified_people: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class VendorDocumentRead(BaseModel):
    id: uuid.UUID
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VendorMeetingCreate(BaseModel):
    meeting_for: str
    description: str | None = None
    contact_id: uuid.UUID | None = None
    attendee_ids: list[uuid.UUID] = []
    guest_attendees: list[str] = []
    start_time: datetime | None = None
    duration_minutes: int | None = None


class VendorMeetingRead(VendorMeetingCreate):
    id: uuid.UUID
    contact_name: str | None = None
    attendee_names: list[str] = []
    created_by_id: uuid.UUID | None = None
    created_by_name: str | None = None

    model_config = {"from_attributes": True}


class VendorBankAccountCreate(BaseModel):
    account_holder_name: str
    bank_name: str
    account_number: str
    account_type: str | None = None
    routing_number: str | None = None
    swift_code: str | None = None
    branch_address: str | None = None
    effective_from: date | None = None
    is_primary: bool = False


class VendorBankAccountRead(VendorBankAccountCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class VendorBase(BaseModel):
    """Every writable business-information field on a vendor."""

    name: str
    specialization: str | None = None
    status: str = "Active"
    federal_id: str | None = None
    website: str | None = None
    contact_number: str | None = None
    email_id: str | None = None
    fax: str | None = None
    vendor_type: str | None = None
    vendor_classification: str | None = None
    payment_terms: str | None = None
    about_vendor: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = "United States"
    zip_code: str | None = None

    primary_business_unit: str | None = None
    business_units: list[str] = []
    vendor_visibility: str = "Organization Level"
    primary_owner_id: uuid.UUID | None = None
    ownership_id: uuid.UUID | None = None
    vendor_lead_id: uuid.UUID | None = None

    send_requirement: bool = False
    send_hotlist: bool = False
    primary_vendor: bool = False
    allow_access_to_all_users: bool = False

    technologies: list[str] = []
    submission_format_fields: list[str] = []
    submission_instructions: str | None = None


class VendorCreate(VendorBase):
    """Create payload — nested sections may be supplied inline by the Add Vendor wizard."""

    accounts: list[VendorAccountCreate] = []
    contacts: list[VendorContactCreate] = []
    notes: list[VendorNoteCreate] = []
    bank_accounts: list[VendorBankAccountCreate] = []


class VendorUpdate(BaseModel):
    name: str | None = None
    specialization: str | None = None
    status: str | None = None
    federal_id: str | None = None
    website: str | None = None
    contact_number: str | None = None
    email_id: str | None = None
    fax: str | None = None
    vendor_type: str | None = None
    vendor_classification: str | None = None
    payment_terms: str | None = None
    about_vendor: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None

    primary_business_unit: str | None = None
    business_units: list[str] | None = None
    vendor_visibility: str | None = None
    primary_owner_id: uuid.UUID | None = None
    ownership_id: uuid.UUID | None = None
    vendor_lead_id: uuid.UUID | None = None

    send_requirement: bool | None = None
    send_hotlist: bool | None = None
    primary_vendor: bool | None = None
    allow_access_to_all_users: bool | None = None

    technologies: list[str] | None = None
    submission_format_fields: list[str] | None = None
    submission_instructions: str | None = None


class VendorRead(VendorBase):
    id: uuid.UUID
    organization_id: uuid.UUID

    primary_owner_name: str | None = None
    ownership_name: str | None = None
    vendor_lead_name: str | None = None

    created_by: uuid.UUID | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None = None
    updated_by_name: str | None = None

    contacts: list[VendorContactRead] = []
    accounts: list[VendorAccountRead] = []
    bank_accounts: list[VendorBankAccountRead] = []
    active_submissions: int = 0

    model_config = {"from_attributes": True}
