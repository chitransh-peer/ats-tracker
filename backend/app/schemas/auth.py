import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    """`reset_token` is only ever populated in non-production when
    `expose_password_reset_token` is enabled; otherwise it stays null so the
    response is identical whether or not the email matched an account."""

    detail: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class ViewAsRequest(BaseModel):
    role_name: str


class ViewAsResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    """Identity resolved from the access token's claims only.

    Does not include email/full_name — those live in the DB record, not the
    JWT, so callers that need them should look up the User by `id`.
    """

    id: uuid.UUID
    organization_id: uuid.UUID
    roles: list[str]
