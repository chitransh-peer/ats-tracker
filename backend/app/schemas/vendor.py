import uuid

from pydantic import BaseModel


class VendorContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None


class VendorContactRead(VendorContactCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class VendorCreate(BaseModel):
    name: str
    specialization: str | None = None
    status: str = "Active"


class VendorUpdate(BaseModel):
    name: str | None = None
    specialization: str | None = None
    status: str | None = None


class VendorRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    specialization: str | None
    status: str
    contacts: list[VendorContactRead]
    active_submissions: int

    model_config = {"from_attributes": True}
