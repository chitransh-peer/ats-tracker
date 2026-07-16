import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str
    department: str | None = None
    client_id: uuid.UUID | None = None
    hiring_manager_id: uuid.UUID | None = None
    recruiter_id: uuid.UUID | None = None
    location: str | None = None
    workplace: str
    employment_type: str
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


class JobRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    req_id: str
    slug: str
    title: str
    department: str | None
    client_id: uuid.UUID | None
    hiring_manager_id: uuid.UUID | None
    recruiter_id: uuid.UUID | None
    stage_template_id: uuid.UUID | None
    location: str | None
    workplace: str
    employment_type: str
    openings: int
    pay_min: int | None
    pay_max: int | None
    priority: str
    status: str
    summary: str | None
    description: str | None
    responsibilities: list[str]
    required_skills: list[str]
    nice_to_have: list[str]
    screening_questions: list[str]
    experience: str | None
    education: str | None
    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    applications_count: int = 0
    shortlisted_count: int = 0
    interviews_count: int = 0
    offers_count: int = 0
    hires_count: int = 0

    model_config = {"from_attributes": True}
