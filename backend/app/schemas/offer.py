import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.application import ApplicationRefs


class OfferCreate(BaseModel):
    application_id: uuid.UUID
    pay_type: str = "Salary"
    base_salary: int | None = Field(default=None, gt=0)
    hourly_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: str = "USD"
    employment_type: str | None = None
    tax_term: str | None = None
    contract_duration: str | None = Field(default=None, max_length=100)
    bonus: int | None = Field(default=None, ge=0)
    equity: str | None = Field(default=None, max_length=100)
    joining_date: date | None = None


class OfferUpdate(BaseModel):
    pay_type: str | None = None
    base_salary: int | None = Field(default=None, gt=0)
    hourly_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: str | None = None
    employment_type: str | None = None
    tax_term: str | None = None
    contract_duration: str | None = Field(default=None, max_length=100)
    bonus: int | None = Field(default=None, ge=0)
    equity: str | None = Field(default=None, max_length=100)
    joining_date: date | None = None


class OfferApprovalDecision(BaseModel):
    note: str | None = None


class OfferVersionRead(BaseModel):
    id: uuid.UUID
    version_number: int
    pay_type: str
    base_salary: int | None
    hourly_rate: float | None
    currency: str
    employment_type: str | None
    tax_term: str | None
    contract_duration: str | None
    bonus: int | None
    equity: str | None
    joining_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OfferApprovalRead(BaseModel):
    id: uuid.UUID
    requested_by: uuid.UUID | None
    approver_id: uuid.UUID | None
    status: str
    note: str | None
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OfferRead(ApplicationRefs):
    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    status: str
    pay_type: str
    base_salary: int | None
    hourly_rate: float | None
    currency: str
    employment_type: str | None
    tax_term: str | None
    contract_duration: str | None
    bonus: int | None
    equity: str | None
    joining_date: date | None
    versions: list[OfferVersionRead]
    approvals: list[OfferApprovalRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
