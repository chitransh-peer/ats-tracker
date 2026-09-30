import uuid
from datetime import datetime

from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    source: str | None = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    current_stage_id: uuid.UUID | None
    source: str | None
    status: str
    applied_at: datetime

    model_config = {"from_attributes": True}


class ApplicationLabels(BaseModel):
    """Who and what an application is for, filled in by list endpoints so a
    page can show names without loading every candidate and job to look them up."""

    candidate_name: str | None = None
    job_title: str | None = None
    job_req_id: str | None = None


class ApplicationListItem(ApplicationLabels, ApplicationRead):
    ai_score: float | None = None
    ai_recommendation: str | None = None


class ApplicationOption(BaseModel):
    id: uuid.UUID
    candidate_name: str
    job_title: str


class ApplicationRefs(BaseModel):
    """The application's candidate and job, with names, on interview, offer
    and onboarding reads."""

    candidate_id: uuid.UUID | None = None
    candidate_name: str | None = None
    job_id: uuid.UUID | None = None
    job_title: str | None = None


class ApplicationStageHistoryRead(BaseModel):
    id: uuid.UUID
    from_stage_id: uuid.UUID | None
    to_stage_id: uuid.UUID | None
    changed_by: uuid.UUID | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkApplicationActionRequest(BaseModel):
    application_ids: list[uuid.UUID]
    note: str | None = None


class BulkActionFailure(BaseModel):
    application_id: uuid.UUID
    reason: str


class BulkActionResult(BaseModel):
    succeeded: list[uuid.UUID]
    failed: list[BulkActionFailure]
