import uuid
from datetime import date, datetime

from pydantic import BaseModel


class OfferCreate(BaseModel):
    application_id: uuid.UUID
    base_salary: int
    bonus: int | None = None
    equity: str | None = None
    joining_date: date | None = None


class OfferUpdate(BaseModel):
    base_salary: int | None = None
    bonus: int | None = None
    equity: str | None = None
    joining_date: date | None = None


class OfferApprovalDecision(BaseModel):
    note: str | None = None


class OfferVersionRead(BaseModel):
    id: uuid.UUID
    version_number: int
    base_salary: int
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


class OfferRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    status: str
    base_salary: int
    bonus: int | None
    equity: str | None
    joining_date: date | None
    versions: list[OfferVersionRead]
    approvals: list[OfferApprovalRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
