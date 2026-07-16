import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    application_id: uuid.UUID
    round_name: str
    mode: str
    scheduled_at: datetime
    panel_user_ids: list[uuid.UUID] = Field(default_factory=list)
    primary_interviewer_id: uuid.UUID | None = None


class InterviewUpdate(BaseModel):
    round_name: str | None = None
    mode: str | None = None
    scheduled_at: datetime | None = None
    status: str | None = None


class InterviewFeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    recommendation: str
    notes: str | None = None


class InterviewFeedbackRead(BaseModel):
    id: uuid.UUID
    submitted_by: uuid.UUID | None
    rating: int
    recommendation: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewPanelMemberRead(BaseModel):
    user_id: uuid.UUID
    is_primary: bool

    model_config = {"from_attributes": True}


class InterviewRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    round_name: str
    mode: str
    scheduled_at: datetime
    status: str
    panel_members: list[InterviewPanelMemberRead]
    feedback_entries: list[InterviewFeedbackRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsolidatedFeedbackRead(BaseModel):
    interview_id: uuid.UUID
    average_rating: float | None
    recommendation_counts: dict[str, int]
    feedback_entries: list[InterviewFeedbackRead]
