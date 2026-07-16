import uuid
from datetime import datetime

from pydantic import BaseModel


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignRolesRequest(BaseModel):
    role_names: list[str]
