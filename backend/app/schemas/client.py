import uuid

from pydantic import BaseModel


class ClientContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None


class ClientContactRead(ClientContactCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ClientCreate(BaseModel):
    name: str
    industry: str | None = None
    status: str = "Active"


class ClientUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    status: str | None = None


class ClientRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    industry: str | None
    status: str
    contacts: list[ClientContactRead]
    active_jobs: int

    model_config = {"from_attributes": True}
