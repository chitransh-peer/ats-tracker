from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import PermissionAction, PermissionResource, RoleName
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.permissions import ROLE_PERMISSIONS
from app.db.models.role import Permission, Role, RolePermission


def seed_roles_and_permissions(db: Session, *, reset_existing_roles: bool = False) -> None:
    """Ensure the permission catalogue exists and bootstrap any missing role.

    Default grants are applied only to roles this call actually creates. A role
    that is already there is left exactly as it is, because a Super Admin can
    edit role permissions from the UI, and this runs on every container start --
    re-applying the defaults would silently restore any permission they had
    deliberately revoked, on the next cold start.

    Pass reset_existing_roles=True to put every role back to its shipped
    defaults, discarding those edits. Nothing does that automatically.
    """
    existing_permissions = {p.key: p for p in db.scalars(select(Permission)).all()}

    # The catalogue is maintained unconditionally: the role editor lists every
    # known permission, so a release that introduces one must be able to offer
    # it even though no role is granted it yet.
    for grants in ROLE_PERMISSIONS.values():
        for resource, action in grants:
            key = f"{resource.value}:{action.value}"
            if key not in existing_permissions:
                permission = Permission(resource=resource.value, action=action.value)
                db.add(permission)
                db.flush()
                existing_permissions[key] = permission

    for role_enum, grants in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_enum.value))
        is_new = role is None
        if is_new:
            role = Role(name=role_enum.value, display_name=role_enum.value.replace("_", " ").title())
            db.add(role)
            db.flush()

        if not is_new and not reset_existing_roles:
            continue

        granted_keys = {f"{resource.value}:{action.value}" for resource, action in grants}
        existing_role_permission_keys = {
            rp.permission.key
            for rp in db.scalars(
                select(RolePermission)
                .where(RolePermission.role_id == role.id)
                .options(selectinload(RolePermission.permission))
            ).all()
        }

        for key in granted_keys - existing_role_permission_keys:
            db.add(RolePermission(role_id=role.id, permission_id=existing_permissions[key].id))

    db.commit()


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def list_roles(db: Session) -> list[Role]:
    return list(
        db.scalars(select(Role).options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))).all()
    )


def get_role(db: Session, role_id) -> Role:
    role = db.scalar(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    if role is None:
        raise NotFoundError("Role not found")
    return role


def roles_grant(db: Session, role_names: list[str], resource: PermissionResource, action: PermissionAction) -> bool:
    """Authoritative runtime permission check, backed by the DB role_permissions
    table (not the static matrix), so super-admin edits take effect immediately.

    A role satisfies the check when it holds the exact (resource, action) grant or
    a (resource, manage) grant, which is treated as a superset of all actions.
    """
    if not role_names:
        return False
    count = db.scalar(
        select(Permission.id)
        .select_from(RolePermission)
        .join(Role, Role.id == RolePermission.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            Role.name.in_(role_names),
            Permission.resource == resource.value,
            Permission.action.in_([action.value, PermissionAction.MANAGE.value]),
        )
        .limit(1)
    )
    return count is not None


def set_role_permissions(db: Session, role: Role, grants: list[tuple[str, str]]) -> Role:
    """Replace a role's permission grants with `grants` (list of (resource, action)).

    The super_admin role is intentionally immutable to prevent an accidental
    lockout of the only role that can manage permissions.
    """
    if role.name == RoleName.SUPER_ADMIN.value:
        raise ValidationAppError("The Super Admin role's permissions cannot be modified")

    valid_resources = {r.value for r in PermissionResource}
    valid_actions = {a.value for a in PermissionAction}
    normalized: set[tuple[str, str]] = set()
    for resource, action in grants:
        if resource not in valid_resources or action not in valid_actions:
            raise ValidationAppError(f"Unknown permission '{resource}:{action}'")
        normalized.add((resource, action))

    existing_permissions = {p.key: p for p in db.scalars(select(Permission)).all()}

    # Drop all current grants for this role, then re-add the requested set.
    for rp in list(role.role_permissions):
        db.delete(rp)
    db.flush()

    for resource, action in normalized:
        key = f"{resource}:{action}"
        permission = existing_permissions.get(key)
        if permission is None:
            permission = Permission(resource=resource, action=action)
            db.add(permission)
            db.flush()
            existing_permissions[key] = permission
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()
    return get_role(db, role.id)
