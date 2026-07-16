import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import AuditAction, InvitationStatus
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.invitation import Invitation
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
            expires_at=datetime.fromtimestamp(decoded["exp"], tz=timezone.utc),
        )
    )


def _issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    roles = role_names_for_user(user)
    access_token = create_access_token(str(user.id), str(user.organization_id), roles)
    refresh_token = create_refresh_token(str(user.id))
    _store_refresh_token(db, user.id, refresh_token)
    return access_token, refresh_token


def login(db: Session, *, email: str, password: str, ip_address: str | None) -> tuple[str, str]:
    user = get_user_by_email_any_org(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")

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
        raise UnauthorizedError("Invalid or expired refresh token")

    if decoded.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token)))
    if stored is None or not stored.is_active or stored.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token has been revoked or expired")

    user = db.get(User, uuid.UUID(decoded["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired refresh token")

    stored.revoked_at = datetime.now(timezone.utc)
    access_token, new_refresh_token = _issue_token_pair(db, user)
    db.commit()
    return access_token, new_refresh_token


def logout(db: Session, *, refresh_token: str) -> None:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token)))
    if stored is not None and stored.is_active:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


def create_invitation(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email: str,
    role_name: str,
    invited_by: uuid.UUID,
    expires_in_days: int = 7,
) -> str:
    role = get_role_by_name(db, role_name)
    if role is None:
        raise ValidationAppError(f"Unknown role: {role_name}")
    if get_user_by_email(db, organization_id, email) is not None:
        raise ConflictError("A user with this email already exists in this organization")

    raw_token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=organization_id,
        email=email,
        role_id=role.id,
        invited_by=invited_by,
        token_hash=_hash_token(raw_token),
        status=InvitationStatus.PENDING.value,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
    )
    db.add(invitation)
    record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=invited_by,
        action=AuditAction.USER_INVITED.value,
        resource_type="invitation",
        metadata={"email": email, "role": role_name},
    )
    db.commit()
    return raw_token


def accept_invitation(db: Session, *, token: str, full_name: str, password: str) -> User:
    invitation = db.scalar(select(Invitation).where(Invitation.token_hash == _hash_token(token)))
    if invitation is None or invitation.status != InvitationStatus.PENDING.value:
        raise UnauthorizedError("Invalid or expired invitation")
    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = InvitationStatus.EXPIRED.value
        db.commit()
        raise UnauthorizedError("This invitation has expired")

    user = User(
        organization_id=invitation.organization_id,
        email=invitation.email,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.flush()

    db.add(UserRole(user_id=user.id, role_id=invitation.role_id))

    invitation.status = InvitationStatus.ACCEPTED.value
    invitation.accepted_at = datetime.now(timezone.utc)

    record_audit(
        db,
        organization_id=invitation.organization_id,
        actor_user_id=user.id,
        action=AuditAction.USER_ACTIVATED.value,
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()
    db.refresh(user)
    return user


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
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
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
    if reset_token is None or reset_token.used_at is not None or reset_token.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Invalid or expired reset token")

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired reset token")

    user.hashed_password = hash_password(new_password)
    reset_token.used_at = datetime.now(timezone.utc)

    db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
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
