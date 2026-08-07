import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ClientContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    status: str = "Active"


class ClientContactRead(ClientContactCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ClientAccountCreate(BaseModel):
    contact_person: str
    email_id: str | None = None
    designation: str | None = None
    office_number: str | None = None
    mobile_number: str | None = None


class ClientAccountRead(ClientAccountCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ClientNoteCreate(BaseModel):
    body: str
    note_type: str = "Client"
    priority: str = "Normal"


class ClientNoteRead(BaseModel):
    id: uuid.UUID
    body: str
    note_type: str
    priority: str
    author_id: uuid.UUID | None
    author_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientDocumentRead(BaseModel):
    id: uuid.UUID
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientAssignmentCreate(BaseModel):
    user_id: uuid.UUID
    assignment_role: str | None = None


class ClientAssignmentRead(ClientAssignmentCreate):
    id: uuid.UUID
    user_name: str | None = None

    model_config = {"from_attributes": True}


class ClientBase(BaseModel):
    """Every writable business-information field on a client."""

    name: str
    short_name: str | None = None
    vms_client_name: str | None = None
    federal_id: str | None = None
    contact_number: str | None = None
    email_id: str | None = None
    fax: str | None = None
    website: str | None = None
    industry: str | None = None
    status: str = "Active"
    category: str | None = None
    practice: str | None = None
    payment_terms: str | None = None
    about_company: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = "United States"
    postal_code: str | None = None

    primary_business_unit: str | None = None
    business_unit: str | None = None
    client_visibility: str = "Organization Level"
    primary_owner_id: uuid.UUID | None = None
    ownership_id: uuid.UUID | None = None
    client_lead_id: uuid.UUID | None = None
    parent_client_id: uuid.UUID | None = None

    display_on_job_posting: bool = True
    send_requirement: bool = True
    send_hotlist: bool = True
    allow_access_to_all_users: bool = False
    notify_near_client_location: bool = False
    stop_contact_email_on_submit: bool = False
    default_address_for_jobs: bool = False

    client_facilities: list[str] = []
    required_documents: list[str] = []
    submission_format_fields: list[str] = []

    guidelines: str | None = None
    markup_percentage: Decimal | None = None
    overtime_markup_percentage: Decimal | None = None
    standard_working_hours: int | None = None
    submission_instructions: str | None = None


class ClientCreate(ClientBase):
    """Create payload — nested sections may be supplied inline by the New Client wizard."""

    accounts: list[ClientAccountCreate] = []
    contacts: list[ClientContactCreate] = []
    notes: list[ClientNoteCreate] = []
    assignments: list[ClientAssignmentCreate] = []


class ClientUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    vms_client_name: str | None = None
    federal_id: str | None = None
    contact_number: str | None = None
    email_id: str | None = None
    fax: str | None = None
    website: str | None = None
    industry: str | None = None
    status: str | None = None
    category: str | None = None
    practice: str | None = None
    payment_terms: str | None = None
    about_company: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    primary_business_unit: str | None = None
    business_unit: str | None = None
    client_visibility: str | None = None
    primary_owner_id: uuid.UUID | None = None
    ownership_id: uuid.UUID | None = None
    client_lead_id: uuid.UUID | None = None
    parent_client_id: uuid.UUID | None = None

    display_on_job_posting: bool | None = None
    send_requirement: bool | None = None
    send_hotlist: bool | None = None
    allow_access_to_all_users: bool | None = None
    notify_near_client_location: bool | None = None
    stop_contact_email_on_submit: bool | None = None
    default_address_for_jobs: bool | None = None

    client_facilities: list[str] | None = None
    required_documents: list[str] | None = None
    submission_format_fields: list[str] | None = None

    guidelines: str | None = None
    markup_percentage: Decimal | None = None
    overtime_markup_percentage: Decimal | None = None
    standard_working_hours: int | None = None
    submission_instructions: str | None = None


class ClientRead(ClientBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    client_code: str

    primary_owner_name: str | None = None
    ownership_name: str | None = None
    client_lead_name: str | None = None
    parent_client_name: str | None = None

    created_by: uuid.UUID | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None = None
    updated_by_name: str | None = None

    contacts: list[ClientContactRead] = []
    accounts: list[ClientAccountRead] = []
    assignments: list[ClientAssignmentRead] = []
    active_jobs: int = 0

    model_config = {"from_attributes": True}
