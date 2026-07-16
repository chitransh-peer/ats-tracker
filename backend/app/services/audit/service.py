import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry


def list_logs(
    db: Session,
    organization_id: uuid.UUID,
    *,
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.organization_id == organization_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
    if actor_user_id is not None:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    return list(db.scalars(query).all())
