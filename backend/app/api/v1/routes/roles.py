import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission, require_super_admin
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.role import PermissionRead, RolePermissionsUpdate, RoleRead
from app.services.audit.service import record as record_audit
from app.services.roles import service as role_service

router = APIRouter(tags=["roles"])


def _serialize_role(role) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        is_system_role=role.is_system_role,
        permissions=[
            PermissionRead(resource=rp.permission.resource, action=rp.permission.action)
            for rp in role.role_permissions
        ],
    )


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _=Depends(require_permission(PermissionResource.ROLE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[RoleRead]:
    roles = role_service.list_roles(db)
    return [_serialize_role(role) for role in roles]


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(
    _=Depends(require_permission(PermissionResource.ROLE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[PermissionRead]:
    roles = role_service.list_roles(db)
    seen: dict[str, PermissionRead] = {}
    for role in roles:
        for rp in role.role_permissions:
            key = rp.permission.key
            if key not in seen:
                seen[key] = PermissionRead(resource=rp.permission.resource, action=rp.permission.action)
    return list(seen.values())


@router.put("/roles/{role_id}/permissions", response_model=RoleRead)
def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdate,
    current_user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
) -> RoleRead:
    role = role_service.get_role(db, role_id)
    grants = [(p.resource, p.action) for p in payload.permissions]
    role = role_service.set_role_permissions(db, role, grants)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.PERMISSION_CHANGED.value,
        resource_type="role",
        resource_id=str(role.id),
        metadata={"role": role.name, "permission_count": len(grants)},
    )
    db.commit()
    return _serialize_role(role)
