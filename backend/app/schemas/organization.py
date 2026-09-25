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


class EmailTestResult(BaseModel):
    """Outcome of a deliberate test send, with the provider's reason on failure."""

    sent: bool
    to: str
    detail: str


class SystemStatusRead(BaseModel):
    """What the running service is actually configured with.

    Deliberately reports only booleans and non-sensitive values: whether a
    credential is present, never the credential. It exists so an operator can
    tell what a deployment picked up without shell or console access to the
    host it runs on.
    """

    app_env: str
    app_base_url: str
    cors_origins: list[str]

    mail_enabled: bool
    smtp_host: str | None
    smtp_port: int
    smtp_credentials_set: bool
    mail_from_email: str

    ai_provider: str
    ai_model: str | None
    ai_credentials_set: bool

    storage_backend: str
    storage_endpoint_url: str | None
    storage_bucket: str
    storage_credentials_set: bool

    redis_configured: bool
    embeddings_enabled: bool

    database_backend: str
    database_host: str | None
