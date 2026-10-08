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
    # True while the account still holds the temporary password it was invited
    # with. The frontend uses it to route straight to the change-password screen;
    # the API enforces the same thing independently.
    must_change_password: bool = False
    roles: list[str]
    created_at: datetime
    updated_at: datetime
    # Set on /auth/me only: whether this user may download original document
    # files, or only preview them in the app.
    can_download_documents: bool | None = None

    model_config = {"from_attributes": True}


class AssignRolesRequest(BaseModel):
    role_names: list[str]
