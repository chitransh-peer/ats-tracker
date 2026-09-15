import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class BenchProfileCreate(BaseModel):
    candidate_id: uuid.UUID
    marketing_title: str | None = None
    status: str | None = None
    sub_status: str | None = None
    bench_start_date: date | None = None
    available_from: date | None = None
    desired_rate: float | None = Field(default=None, ge=0)
    rate_currency: str | None = None
    rate_unit: str | None = None
    tax_term: str | None = None
    sales_team_member_id: uuid.UUID | None = None
    account_manager_id: uuid.UUID | None = None
    preferred_locations: str | None = None
    willing_to_relocate: bool | None = None
    marketing_summary: str | None = None
    internal_notes: str | None = None
    owner_ids: list[uuid.UUID] | None = None


class BenchProfileUpdate(BaseModel):
    marketing_title: str | None = None
    status: str | None = None
    sub_status: str | None = None
    bench_start_date: date | None = None
    available_from: date | None = None
    desired_rate: float | None = Field(default=None, ge=0)
    rate_currency: str | None = None
    rate_unit: str | None = None
    tax_term: str | None = None
    sales_team_member_id: uuid.UUID | None = None
    account_manager_id: uuid.UUID | None = None
    preferred_locations: str | None = None
    willing_to_relocate: bool | None = None
    marketing_summary: str | None = None
    internal_notes: str | None = None
    owner_ids: list[uuid.UUID] | None = None


class BenchSubmissionCreate(BaseModel):
    client_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    submitted_rate: float | None = Field(default=None, ge=0)
    status: str | None = None
    note: str | None = None


class BenchSubmissionRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID | None
    vendor_id: uuid.UUID | None
    job_id: uuid.UUID | None
    submitted_rate: float | None
    status: str | None
    note: str | None
    submitted_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BenchProfileRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    candidate_id: uuid.UUID
    bench_code: int

    # Flattened from the candidate so the bench grid needs one request, not N.
    full_name: str
    email: str
    phone: str | None
    location: str | None
    current_title: str | None
    work_auth: str | None
    total_experience_years: float | None
    skills: list[str]

    marketing_title: str | None
    status: str
    sub_status: str | None
    bench_start_date: date
    bench_age_days: int
    available_from: date | None

    desired_rate: float | None
    rate_currency: str
    rate_unit: str | None
    tax_term: str | None

    sales_team_member_id: uuid.UUID | None
    account_manager_id: uuid.UUID | None
    owner_ids: list[uuid.UUID]

    preferred_locations: str | None
    willing_to_relocate: bool
    marketing_summary: str | None
    internal_notes: str | None

    created_at: datetime
    updated_at: datetime


class BenchSummary(BaseModel):
    total: int
    active: int
    inactive: int
    placed: int
    average_bench_age_days: float | None
    aging_over_60_days: int


class BulkAddToBenchRequest(BaseModel):
    candidate_ids: list[uuid.UUID]


class BulkBenchFailure(BaseModel):
    candidate_id: uuid.UUID
    reason: str


class BulkBenchResult(BaseModel):
    succeeded: list[uuid.UUID]
    failed: list[BulkBenchFailure]
