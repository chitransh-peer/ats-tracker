import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import AuditAction
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.refresh_token import RefreshToken
from app.db.models.role import UserRole
from app.db.models.user import User
from app.services.audit.service import record as record_audit
from app.services.roles.service import get_role_by_name
from app.services.users.service import get_user_by_email, get_user_by_email_any_org, role_names_for_user

_settings = get_settings()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _store_refresh_token(db: Session, user_id: uuid.UUID, refresh_token: str) -> None:
    decoded = decode_token(refresh_token)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash_token(refresh_token),
            expires_at=datetime.fromtimestamp(decoded["exp"], tz=UTC),
        )
    )


def _issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    roles = role_names_for_user(user)
    access_token = create_access_token(
        str(user.id), str(user.organization_id), roles, must_change_password=user.must_change_password
    )
    refresh_token = create_refresh_token(str(user.id))
    _store_refresh_token(db, user.id, refresh_token)
    return access_token, refresh_token


def login(db: Session, *, email: str, password: str, ip_address: str | None) -> tuple[str, str]:
    user = get_user_by_email_any_org(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")
    # Only a temporary password carries a deadline; a password the user chose
    # themselves has temp_password_expires_at set back to None and never expires.
    if (
        user.must_change_password
        and user.temp_password_expires_at is not None
        and user.temp_password_expires_at < datetime.now(UTC)
    ):
        raise UnauthorizedError("This temporary password has expired. Ask your administrator to send a new invitation.")

    access_token, refresh_token = _issue_token_pair(db, user)
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=AuditAction.LOGIN.value,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    db.commit()
    return access_token, refresh_token


def refresh(db: Session, *, refresh_token: str) -> tuple[str, str]:
    try:
        decoded = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired refresh token") from None

    if decoded.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token)))
    if stored is None or not stored.is_active or stored.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token has been revoked or expired")

    user = db.get(User, uuid.UUID(decoded["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired refresh token")

    stored.revoked_at = datetime.now(UTC)
    access_token, new_refresh_token = _issue_token_pair(db, user)
    db.commit()
    return access_token, new_refresh_token


def logout(db: Session, *, refresh_token: str) -> None:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token)))
    if stored is not None and stored.is_active:
        stored.revoked_at = datetime.now(UTC)
        db.commit()


def issue_tokens_for(db: Session, user: User) -> tuple[str, str]:
    """Mint a fresh token pair for an already-authenticated user.

    Used after a password change, which revokes every outstanding refresh token
    and leaves the caller's access token carrying stale claims.
    """
    access_token, refresh_token = _issue_token_pair(db, user)
    db.commit()
    return access_token, refresh_token


def _generate_temp_password() -> str:
    """A readable one-time password.

    token_urlsafe can emit look-alike characters that are easy to mistype when
    someone copies the password out of an email by hand, so the alphabet drops
    the usual offenders (0/O, 1/l/I) and the value is grouped for legibility.
    18 characters drawn from a 54-symbol alphabet is about 103 bits of entropy,
    well beyond what a 72-hour, single-use credential needs.
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    groups = ["".join(secrets.choice(alphabet) for _ in range(6)) for _ in range(3)]
    return "-".join(groups)


def invite_user(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email: str,
    full_name: str,
    role_name: str,
    invited_by: uuid.UUID,
    expires_in_hours: int = 72,
) -> tuple[User, str]:
    """Create the account up front and return it with its temporary password.

    The account is live immediately rather than waiting on an acceptance step:
    must_change_password keeps it walled off from everything except the password
    change until the person picks their own. The raw password is returned once,
    for the invitation email, and is never recoverable afterwards -- only its
    hash is stored.
    """
    role = get_role_by_name(db, role_name)
    if role is None:
        raise ValidationAppError(f"Unknown role: {role_name}")
    if get_user_by_email(db, organization_id, email) is not None:
        raise ConflictError("A user with this email already exists in this organization")

    temp_password = _generate_temp_password()
    user = User(
        organization_id=organization_id,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(temp_password),
        must_change_password=True,
        temp_password_expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
    )
    db.add(user)
    db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id))

    record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=invited_by,
        action=AuditAction.USER_INVITED.value,
        resource_type="user",
        resource_id=str(user.id),
        metadata={"email": email, "role": role_name},
    )
    db.commit()
    db.refresh(user)
    return user, temp_password


def change_password(db: Session, *, user: User, current_password: str, new_password: str) -> bool:
    """Set a user's own password, clearing any temporary-password state.

    Returns whether this call completed an invitation, so the caller can send the
    welcome mail exactly once. Verifying the current password matters most here
    for the invited case: it proves the person holds the emailed credential and
    not merely a session someone left open.
    """
    if not verify_password(current_password, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")
    if verify_password(new_password, user.hashed_password):
        raise ValidationAppError("Your new password must be different from your current one")

    was_invited = user.must_change_password
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    user.temp_password_expires_at = None

    # Any session opened with the old password is no longer trustworthy -- the
    # temporary one travelled by email and may have been seen by someone else.
    db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=(AuditAction.USER_ACTIVATED if was_invited else AuditAction.PASSWORD_RESET_COMPLETED).value,
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()
    return was_invited


def request_password_reset(db: Session, *, email: str, expires_in_minutes: int = 30) -> str | None:
    """Returns the raw reset token, or None if no matching active user exists.

    Callers must not reveal whether the email matched, to avoid leaking account existence.
    """
    user = get_user_by_email_any_org(db, email)
    if user is None or not user.is_active:
        return None

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=expires_in_minutes),
        )
    )
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=AuditAction.PASSWORD_RESET_REQUESTED.value,
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()
    return raw_token


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    reset_token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token)))
    if reset_token is None or reset_token.used_at is not None or reset_token.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Invalid or expired reset token")

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired reset token")

    user.hashed_password = hash_password(new_password)
    reset_token.used_at = datetime.now(UTC)
    # Someone who never used their temporary password can recover through the
    # ordinary forgot-password flow. They have just chosen a password of their
    # own, so the invitation is complete and the gate must not stay closed.
    user.must_change_password = False
    user.temp_password_expires_at = None

    db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=AuditAction.PASSWORD_RESET_COMPLETED.value,
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()
