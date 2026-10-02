import uuid
from datetime import datetime

from pydantic import BaseModel


class ApplicationQuestion(BaseModel):
    key: str
    label: str
    type: str  # text | textarea | number | yesno
    required: bool
    placeholder: str | None = None


class PublicJobRead(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    department: str | None
    location: str | None
    workplace: str
    employment_type: str
    summary: str | None
    description: str | None
    responsibilities: list[str]
    required_skills: list[str]
    nice_to_have: list[str]
    experience: str | None
    education: str | None
    screening_questions: list[str]
    posted_at: datetime | None
    # The JD-dependent part of the application form, built per request.
    role_questions: list[ApplicationQuestion] = []
    ask_portfolio_links: bool = False
    ask_sponsorship: bool = False

    model_config = {"from_attributes": True}


class PublicOrganizationRead(BaseModel):
    name: str
    slug: str

    model_config = {"from_attributes": True}


class PublicApplyResponse(BaseModel):
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
