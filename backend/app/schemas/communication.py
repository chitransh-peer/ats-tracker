import uuid
from datetime import datetime

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    type: str
    subject: str
    body: str


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body: str | None = None


class TemplateRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    type: str
    subject: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    candidate_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    subject: str
    body: str


class OutboundMessageRead(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID | None
    application_id: uuid.UUID | None
    template_id: uuid.UUID | None
    subject: str
    body: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
