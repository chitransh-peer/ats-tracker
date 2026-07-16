from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.role import PermissionRead, RoleRead
from app.services.roles import service as role_service

router = APIRouter(tags=["roles"])


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _=Depends(require_permission(PermissionResource.ROLE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[RoleRead]:
    roles = role_service.list_roles(db)
    return [
        RoleRead(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            is_system_role=role.is_system_role,
            permissions=[
                PermissionRead(resource=rp.permission.resource, action=rp.permission.action)
                for rp in role.role_permissions
            ],
        )
        for role in roles
    ]


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
