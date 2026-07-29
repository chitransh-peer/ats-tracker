import uuid
from datetime import date, datetime

from pydantic import BaseModel


class OnboardingTaskCreate(BaseModel):
    title: str
    category: str
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class OnboardingTaskUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    status: str | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class OnboardingCaseUpdate(BaseModel):
    start_date: date | None = None
    coordinator_id: uuid.UUID | None = None
    notes: str | None = None


class OnboardingTaskRead(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    category: str
    status: str
    assignee_id: uuid.UUID | None
    due_date: date | None
    order_index: int
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OnboardingCaseRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    status: str
    start_date: date | None
    coordinator_id: uuid.UUID | None
    notes: str | None
    completed_at: datetime | None
    tasks: list[OnboardingTaskRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
