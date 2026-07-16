import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.security import hash_password
from app.db.models.role import Role, UserRole
from app.db.models.user import User
from app.services.roles.service import get_role_by_name


def get_user_by_email(db: Session, organization_id: uuid.UUID, email: str) -> User | None:
    return db.scalar(
        select(User).where(User.organization_id == organization_id, User.email == email, User.deleted_at.is_(None))
    )


def get_user_by_email_any_org(db: Session, email: str) -> User | None:
    """Login-time lookup that doesn't yet know the caller's organization.

    Email is only unique per-organization, so this is a simplification valid
    while the product is internal/single-tenant; true multi-tenant SaaS will
    need tenant resolution (subdomain, org picker) before this can be dropped.
    """
    return db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))


def get_user_by_id(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id, User.organization_id == organization_id, User.deleted_at.is_(None))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )
    if user is None:
        raise NotFoundError("User not found")
    return user


def list_users(db: Session, organization_id: uuid.UUID) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.organization_id == organization_id, User.deleted_at.is_(None))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        ).all()
    )


def role_names_for_user(user: User) -> list[str]:
    return [ur.role.name for ur in user.user_roles]


def create_user(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email: str,
    full_name: str,
    password: str,
    role_names: list[str],
) -> User:
    if get_user_by_email(db, organization_id, email) is not None:
        raise ConflictError("A user with this email already exists in this organization")

    user = User(
        organization_id=organization_id,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.flush()

    _assign_roles(db, user, role_names)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, *, full_name: str | None, is_active: bool | None) -> User:
    if full_name is not None:
        user.full_name = full_name
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def assign_roles(db: Session, user: User, role_names: list[str]) -> User:
    for ur in list(user.user_roles):
        db.delete(ur)
    db.flush()
    _assign_roles(db, user, role_names)
    db.commit()
    db.refresh(user)
    return user


def _assign_roles(db: Session, user: User, role_names: list[str]) -> None:
    for role_name in role_names:
        role = get_role_by_name(db, role_name)
        if role is None:
            raise ValidationAppError(f"Unknown role: {role_name}")
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
