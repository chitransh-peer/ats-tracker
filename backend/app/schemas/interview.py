import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.application import ApplicationRefs

# The zones an interview can be scheduled in: the US and India teams the
# product serves, plus the other countries jobs can be posted in. A fixed list
# rather than every IANA zone keeps the picker short and needs no tz database
# on the server. Mirrored in Frontend/lib/timezones.ts.
INTERVIEW_TIMEZONES = (
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Phoenix",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    "America/Toronto",
    "America/Vancouver",
    "Asia/Kolkata",
    "Europe/London",
    "Australia/Sydney",
    "UTC",
)


def _check_timezone(value: str | None) -> str | None:
    if value is not None and value not in INTERVIEW_TIMEZONES:
        raise ValueError(f"Unsupported time zone: {value}")
    return value


def _check_link(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not value.lower().startswith(("https://", "http://")):
        raise ValueError("Meeting link must start with https:// or http://")
    return value


class _SchedulingFields(BaseModel):
    timezone: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    meeting_link: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=500)

    _timezone = field_validator("timezone")(_check_timezone)
    _link = field_validator("meeting_link")(_check_link)


class InterviewCreate(_SchedulingFields):
    application_id: uuid.UUID
    round_name: str
    mode: str
    scheduled_at: datetime
    panel_user_ids: list[uuid.UUID] = Field(default_factory=list)
    primary_interviewer_id: uuid.UUID | None = None


class InterviewUpdate(_SchedulingFields):
    round_name: str | None = None
    mode: str | None = None
    scheduled_at: datetime | None = None
    status: str | None = None
    # When sent, replaces the panel; the primary must be one of them.
    panel_user_ids: list[uuid.UUID] | None = None
    primary_interviewer_id: uuid.UUID | None = None


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
    full_name: str | None = None
    is_primary: bool

    model_config = {"from_attributes": True}


class InterviewRead(ApplicationRefs):
    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    round_name: str
    mode: str
    scheduled_at: datetime
    status: str
    timezone: str | None = None
    duration_minutes: int | None = None
    meeting_link: str | None = None
    location: str | None = None
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
