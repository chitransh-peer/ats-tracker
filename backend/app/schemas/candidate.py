import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    degree: str
    school: str
    year: str | None = None


class CandidateCreate(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    total_experience_years: float | None = None
    relevant_experience_years: float | None = None
    notice_period: str | None = None
    current_ctc: int | None = None
    expected_ctc: int | None = None
    skills: list[str] = Field(default_factory=list)
    source: str | None = None
    linkedin_url: str | None = None
    work_auth: str | None = None
    relocation_ok: bool = False
    education: list[EducationItem] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    total_experience_years: float | None = None
    relevant_experience_years: float | None = None
    notice_period: str | None = None
    current_ctc: int | None = None
    expected_ctc: int | None = None
    skills: list[str] | None = None
    rating: int | None = None
    linkedin_url: str | None = None
    work_auth: str | None = None
    relocation_ok: bool | None = None
    status: str | None = None


class CandidateNoteCreate(BaseModel):
    body: str


class CandidateNoteRead(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID | None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateTagsUpdate(BaseModel):
    tags: list[str]


class CandidateDocumentRead(BaseModel):
    id: uuid.UUID
    document_type: str
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DuplicateWarning(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    email: str
    match_reason: str


class CandidateRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    location: str | None
    current_company: str | None
    current_title: str | None
    total_experience_years: float | None
    relevant_experience_years: float | None
    notice_period: str | None
    current_ctc: int | None
    expected_ctc: int | None
    skills: list[str]
    source: str | None
    rating: int | None
    linkedin_url: str | None
    work_auth: str | None
    relocation_ok: bool
    status: str
    education: list[EducationItem]
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    duplicate_warnings: list[DuplicateWarning] = Field(default_factory=list)

    model_config = {"from_attributes": True}
