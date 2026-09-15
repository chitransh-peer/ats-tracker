import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.communication import TemplateCreate, TemplateRead, TemplateUpdate
from app.services.audit.service import record as record_audit
from app.services.communication import service as communication_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateRead])
def list_templates(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.TEMPLATE, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[TemplateRead]:
    return communication_service.list_templates(db, current_user.organization_id)


@router.post("", response_model=TemplateRead, status_code=201)
def create_template(
    payload: TemplateCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.TEMPLATE, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    template = communication_service.create_template(
        db, organization_id=current_user.organization_id, actor_id=current_user.id, **payload.model_dump()
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.TEMPLATE_CREATED.value,
        resource_type="template",
        resource_id=str(template.id),
    )
    db.commit()
    return template


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.TEMPLATE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    template = communication_service.get_template(db, current_user.organization_id, template_id)
    template = communication_service.update_template(db, template, **payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.TEMPLATE_UPDATED.value,
        resource_type="template",
        resource_id=str(template.id),
    )
    db.commit()
    return template


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.TEMPLATE, PermissionAction.DELETE)),
    db: Session = Depends(get_db_session),
) -> None:
    template = communication_service.get_template(db, current_user.organization_id, template_id)
    # Record before the delete so the audit row survives even though the template won't.
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.TEMPLATE_DELETED.value,
        resource_type="template",
        resource_id=str(template.id),
        metadata={"name": template.name, "type": template.type},
    )
    communication_service.delete_template(db, template)
