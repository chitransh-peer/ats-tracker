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


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class InviteAcceptRequest(BaseModel):
    token: str
    full_name: str
    password: str = Field(min_length=8)


class CurrentUser(BaseModel):
    """Identity resolved from the access token's claims only.

    Does not include email/full_name — those live in the DB record, not the
    JWT, so callers that need them should look up the User by `id`.
    """

    id: uuid.UUID
    organization_id: uuid.UUID
    roles: list[str]
