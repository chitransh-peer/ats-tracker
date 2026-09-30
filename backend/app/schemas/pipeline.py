import uuid
from datetime import datetime

from pydantic import BaseModel


class StageRead(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int
    terminal_outcome: str

    model_config = {"from_attributes": True}


class StageTemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    is_default: bool
    stages: list[StageRead]

    model_config = {"from_attributes": True}


class MoveStageRequest(BaseModel):
    to_stage_id: uuid.UUID
    note: str | None = None


class StageActionRequest(BaseModel):
    note: str | None = None


class BoardStageCount(BaseModel):
    stage_id: uuid.UUID
    count: int


class BoardCard(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str | None
    job_id: uuid.UUID
    job_title: str | None
    current_stage_id: uuid.UUID | None
    status: str
    applied_at: datetime


class PipelineBoardRead(BaseModel):
    """`total` counts every application on the board; `cards` holds at most
    `limit` of them, newest first."""

    stage_counts: list[BoardStageCount]
    total: int
    hired: int
    cards: list[BoardCard]
    limit: int
