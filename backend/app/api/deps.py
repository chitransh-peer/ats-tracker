import uuid
from collections.abc import Generator

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.enums import PermissionAction, PermissionResource, RoleName
from app.core.exceptions import ForbiddenError, PasswordChangeRequiredError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.schemas.auth import CurrentUser
from app.services.roles.service import roles_grant

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


# The only routes an account still holding a temporary password may reach.
# Everything else is refused until they have chosen their own password:
# /auth/me so the app can render who they are and why they are being stopped,
# /auth/change-password so they can do something about it, and /auth/logout so
# they are never trapped in a session they cannot leave.
_PASSWORD_CHANGE_EXEMPT_PATHS = frozenset(
    {
        "/api/v1/auth/me",
        "/api/v1/auth/change-password",
        "/api/v1/auth/logout",
    }
)


def get_current_user(
    request: Request,
    token: str | None = Depends(_oauth2_scheme),
) -> CurrentUser:
    if token is None:
        raise UnauthorizedError("Missing authentication token")
    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        # from None: the JWT internals are noise to the caller and shouldn't reach logs.
        raise UnauthorizedError("Invalid or expired token") from None

    if decoded.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    # Enforced here rather than in the frontend so it cannot be stepped around by
    # editing the URL or calling the API directly. Every authenticated route
    # depends on this function, so the gate covers all of them by construction.
    if decoded.get("must_change_password") and request.url.path.rstrip("/") not in _PASSWORD_CHANGE_EXEMPT_PATHS:
        raise PasswordChangeRequiredError()

    return CurrentUser(
        id=uuid.UUID(decoded["sub"]),
        organization_id=uuid.UUID(decoded["org_id"]),
        roles=decoded.get("roles", []),
    )


def require_permission(resource: PermissionResource, action: PermissionAction):
    def _dependency(
        current_user: CurrentUser = Depends(get_current_user),
        db: Session = Depends(get_db_session),
    ) -> CurrentUser:
        if roles_grant(db, current_user.roles, resource, action):
            return current_user
        raise ForbiddenError()

    return _dependency


def require_super_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Gate a route to the Super Admin role only, regardless of the permission matrix."""
    if RoleName.SUPER_ADMIN.value not in current_user.roles:
        raise ForbiddenError()
    return current_user
