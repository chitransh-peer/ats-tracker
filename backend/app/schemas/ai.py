import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ParsedResumeRead(BaseModel):
    id: uuid.UUID
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    total_experience_years: float | None
    skills: list[str]
    education: list[dict]
    work_history: list[dict]
    raw_text: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeParseRunRead(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    document_id: uuid.UUID
    status: str
    error_message: str | None
    model_name: str | None
    created_at: datetime
    completed_at: datetime | None
    parsed_resume: ParsedResumeRead | None = None

    model_config = {"from_attributes": True}


class ParseResumeRequest(BaseModel):
    candidate_id: uuid.UUID
    document_id: uuid.UUID


class AIEvaluationRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    version: int
    status: str
    rule_score: float | None
    semantic_score: float | None
    overall_score: float | None
    recommendation_label: str | None
    strengths: list[str]
    gaps: list[str]
    risk_flags: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    criteria: list[dict] = []
    suggested_interview_questions: list[str]
    confidence: float | None
    explanation_text: str | None
    model_name: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIEvaluationOverrideRequest(BaseModel):
    recommendation_label: str
    note: str | None = None


class JDCriterion(BaseModel):
    type: str
    requirement: str
    weight: float
    candidate_value: str
    status: str
    score: float


class JDResumeComparisonRead(BaseModel):
    job_requirements: dict
    candidate_profile: dict
    criteria: list[JDCriterion]
    total_score: float = Field(ge=0, le=100)
