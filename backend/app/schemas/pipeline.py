import uuid

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
