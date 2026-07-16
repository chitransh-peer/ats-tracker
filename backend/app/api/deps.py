import uuid
from collections.abc import Generator

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.enums import PermissionAction, PermissionResource
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import role_grants
from app.core.security import decode_token
from app.db.session import get_db
from app.schemas.auth import CurrentUser

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
) -> CurrentUser:
    if token is None:
        raise UnauthorizedError("Missing authentication token")
    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token")

    if decoded.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    return CurrentUser(
        id=uuid.UUID(decoded["sub"]),
        organization_id=uuid.UUID(decoded["org_id"]),
        roles=decoded.get("roles", []),
    )


def require_permission(resource: PermissionResource, action: PermissionAction):
    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        from app.core.enums import RoleName

        for role_name in current_user.roles:
            try:
                role_enum = RoleName(role_name)
            except ValueError:
                continue
            if role_grants(role_enum, resource, action):
                return current_user
        raise ForbiddenError()

    return _dependency
