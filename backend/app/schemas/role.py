import uuid

from pydantic import BaseModel


class PermissionRead(BaseModel):
    resource: str
    action: str

    model_config = {"from_attributes": True}


class RoleRead(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    is_system_role: bool
    permissions: list[PermissionRead]

    model_config = {"from_attributes": True}


class PermissionGrant(BaseModel):
    resource: str
    action: str


class RolePermissionsUpdate(BaseModel):
    permissions: list[PermissionGrant]
