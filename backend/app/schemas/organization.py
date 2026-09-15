import uuid

from pydantic import BaseModel


class OrganizationSettingsRead(BaseModel):
    default_locale: str
    careers_page_enabled: bool

    model_config = {"from_attributes": True}


class OrganizationSettingsUpdate(BaseModel):
    default_locale: str | None = None
    careers_page_enabled: bool | None = None


class OrganizationRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    settings: OrganizationSettingsRead

    model_config = {"from_attributes": True}


class EmailStatusRead(BaseModel):
    enabled: bool
    smtp_host: str | None
    from_email: str
    from_name: str
    app_base_url: str
