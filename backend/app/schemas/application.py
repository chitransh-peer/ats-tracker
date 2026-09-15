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


class ApplicationListItem(ApplicationRead):
    ai_score: float | None = None
    ai_recommendation: str | None = None


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
