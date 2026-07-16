import uuid
from datetime import datetime

from pydantic import BaseModel


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

    model_config = {"from_attributes": True}


class PublicApplyResponse(BaseModel):
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
