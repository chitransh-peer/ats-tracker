import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    metadata_json: dict
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditUserSummary(BaseModel):
    actor_user_id: uuid.UUID | None
    full_name: str | None
    email: str | None
    event_count: int
    last_activity: datetime | None
