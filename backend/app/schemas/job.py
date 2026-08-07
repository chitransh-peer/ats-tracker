import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class JobNoteCreate(BaseModel):
    body: str
    note_type: str = "Job Posting"
    action: str | None = None


class JobNoteRead(BaseModel):
    id: uuid.UUID
    body: str
    note_type: str
    action: str | None
    author_id: uuid.UUID | None
    author_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobDocumentRead(BaseModel):
    id: uuid.UUID
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobCustomFieldCreate(BaseModel):
    field_name: str
    field_value: str | None = None


class JobCustomFieldRead(JobCustomFieldCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class JobSearchCriteriaWrite(BaseModel):
    boolean_string: str | None = None
    job_title: str | None = None
    recent_job_title_only: bool = False

    search_mode: str = "radius"
    country: str | None = None
    state: str | None = None
    city: str | None = None
    postal_code: str | None = None
    radius_miles: int | None = None
    search_radius_within_state: bool = False
    include_applicants_without_country: bool = False

    experience_min_years: int | None = None
    experience_max_years: int | None = None
    education: list[str] = Field(default_factory=list)
    work_authorizations: list[str] = Field(default_factory=list)
    employer: str | None = None
    most_recent_employer_only: bool = False
    willing_to_relocate: bool | None = None
    clearance: bool | None = None


class JobSearchCriteriaRead(JobSearchCriteriaWrite):
    id: uuid.UUID
    job_id: uuid.UUID

    model_config = {"from_attributes": True}


class JobSubmissionRead(BaseModel):
    """A row in the job snapshot's Submissions grid."""

    application_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: str | None = None
    candidate_phone: str | None = None
    candidate_location: str | None = None
    work_auth: str | None = None
    pay_expectation: int | None = None
    source: str | None = None
    status: str
    current_stage_id: uuid.UUID | None = None
    current_stage_name: str | None = None
    stage_index: int = 0
    applied_at: datetime
    submitted_by: uuid.UUID | None = None
    submitted_by_name: str | None = None
    submitted_at: datetime | None = None


class JobSubmissionsSummary(BaseModel):
    stages: list[str]
    submissions: list[JobSubmissionRead]
    counts: dict[str, int]


class JobBase(BaseModel):
    """Every writable field on a job posting."""

    title: str
    department: str | None = None
    client_id: uuid.UUID | None = None
    hiring_manager_id: uuid.UUID | None = None
    recruiter_id: uuid.UUID | None = None
    location: str | None = None
    workplace: str = "Onsite"
    employment_type: str = "Full-time"
    openings: int = 1
    pay_min: int | None = None
    pay_max: int | None = None
    priority: str = "Medium"
    summary: str | None = None
    description: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(default_factory=list)
    experience: str | None = None
    education: str | None = None

    # Job details
    business_unit: str | None = None
    facility: str | None = None
    end_client: str | None = None
    job_status_detail: str | None = None
    duration: str | None = None
    required_hours_per_week: int | None = None
    interview_mode: str | None = None
    clearance_required: bool = False
    additional_details: str | None = None
    employment_test_template: str | None = None
    employment_level: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    work_authorizations: list[str] = Field(default_factory=list)

    respond_by: str | None = None
    respond_by_date: date | None = None
    turnaround_time_value: int | None = None
    turnaround_time_unit: str | None = None

    pay_rate_currency: str = "USD"
    pay_rate_unit: str = "Hourly"
    pay_rate_type: str | None = None
    client_bill_rate_min: Decimal | None = None
    client_bill_rate_max: Decimal | None = None
    client_bill_rate_currency: str = "USD"
    client_bill_rate_unit: str = "Hourly"
    client_bill_rate_type: str | None = None

    address: str | None = None
    city: str | None = None
    states: list[str] = Field(default_factory=list)
    country: str | None = "United States"
    postal_code: str | None = None

    experience_min_years: int | None = None
    experience_max_years: int | None = None

    max_allowed_submissions: int | None = None
    tax_terms: list[str] = Field(default_factory=list)
    sales_manager_id: uuid.UUID | None = None
    recruitment_manager_id: uuid.UUID | None = None
    account_manager_id: uuid.UUID | None = None
    primary_recruiter_id: uuid.UUID | None = None
    assigned_to_ids: list[uuid.UUID] = Field(default_factory=list)
    comments: str | None = None


class JobCreate(JobBase):
    """Create payload — nested sections may be supplied inline by the New Job wizard."""

    notes: list[JobNoteCreate] = Field(default_factory=list)
    custom_fields: list[JobCustomFieldCreate] = Field(default_factory=list)
    search_criteria: JobSearchCriteriaWrite | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    client_id: uuid.UUID | None = None
    hiring_manager_id: uuid.UUID | None = None
    recruiter_id: uuid.UUID | None = None
    location: str | None = None
    workplace: str | None = None
    employment_type: str | None = None
    openings: int | None = None
    pay_min: int | None = None
    pay_max: int | None = None
    priority: str | None = None
    summary: str | None = None
    description: str | None = None
    responsibilities: list[str] | None = None
    required_skills: list[str] | None = None
    nice_to_have: list[str] | None = None
    screening_questions: list[str] | None = None
    experience: str | None = None
    education: str | None = None

    business_unit: str | None = None
    facility: str | None = None
    end_client: str | None = None
    job_status_detail: str | None = None
    duration: str | None = None
    required_hours_per_week: int | None = None
    interview_mode: str | None = None
    clearance_required: bool | None = None
    additional_details: str | None = None
    employment_test_template: str | None = None
    employment_level: str | None = None
    required_documents: list[str] | None = None
    work_authorizations: list[str] | None = None

    respond_by: str | None = None
    respond_by_date: date | None = None
    turnaround_time_value: int | None = None
    turnaround_time_unit: str | None = None

    pay_rate_currency: str | None = None
    pay_rate_unit: str | None = None
    pay_rate_type: str | None = None
    client_bill_rate_min: Decimal | None = None
    client_bill_rate_max: Decimal | None = None
    client_bill_rate_currency: str | None = None
    client_bill_rate_unit: str | None = None
    client_bill_rate_type: str | None = None

    address: str | None = None
    city: str | None = None
    states: list[str] | None = None
    country: str | None = None
    postal_code: str | None = None

    experience_min_years: int | None = None
    experience_max_years: int | None = None

    max_allowed_submissions: int | None = None
    tax_terms: list[str] | None = None
    sales_manager_id: uuid.UUID | None = None
    recruitment_manager_id: uuid.UUID | None = None
    account_manager_id: uuid.UUID | None = None
    primary_recruiter_id: uuid.UUID | None = None
    assigned_to_ids: list[uuid.UUID] | None = None
    comments: str | None = None


class JobRead(JobBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    req_id: str
    slug: str
    stage_template_id: uuid.UUID | None = None
    status: str
    posted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    client_name: str | None = None
    sales_manager_name: str | None = None
    recruitment_manager_name: str | None = None
    account_manager_name: str | None = None
    primary_recruiter_name: str | None = None
    assigned_to_names: list[str] = Field(default_factory=list)

    created_by: uuid.UUID | None = None
    created_by_name: str | None = None
    updated_by: uuid.UUID | None = None
    updated_by_name: str | None = None

    job_age_days: int = 0
    custom_fields: list[JobCustomFieldRead] = Field(default_factory=list)
    search_criteria: JobSearchCriteriaRead | None = None

    applications_count: int = 0
    shortlisted_count: int = 0
    interviews_count: int = 0
    offers_count: int = 0
    hires_count: int = 0

    model_config = {"from_attributes": True}
