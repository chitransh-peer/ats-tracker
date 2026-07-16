from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import RoleName
from app.core.permissions import ROLE_PERMISSIONS
from app.db.models.role import Permission, Role, RolePermission


def seed_roles_and_permissions(db: Session) -> None:
    existing_permissions = {p.key: p for p in db.scalars(select(Permission)).all()}

    for role_enum, grants in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_enum.value))
        if role is None:
            role = Role(name=role_enum.value, display_name=role_enum.value.replace("_", " ").title())
            db.add(role)
            db.flush()

        granted_keys = {f"{resource.value}:{action.value}" for resource, action in grants}
        existing_role_permission_keys = {
            rp.permission.key for rp in db.scalars(
                select(RolePermission).where(RolePermission.role_id == role.id).options(selectinload(RolePermission.permission))
            ).all()
        }

        for key in granted_keys - existing_role_permission_keys:
            permission = existing_permissions.get(key)
            if permission is None:
                resource, action = key.split(":")
                permission = Permission(resource=resource, action=action)
                db.add(permission)
                db.flush()
                existing_permissions[key] = permission
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def list_roles(db: Session) -> list[Role]:
    return list(
        db.scalars(
            select(Role).options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        ).all()
    )
