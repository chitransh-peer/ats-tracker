import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.user import User


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


def summarize_by_user(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """One row per actor: their identity plus event count and last activity.

    Powers the per-user audit view so each user's trail can be inspected in
    isolation rather than as one undifferentiated org-wide stream.
    """
    rows = db.execute(
        select(
            AuditLog.actor_user_id,
            User.full_name,
            User.email,
            func.count(AuditLog.id).label("event_count"),
            func.max(AuditLog.created_at).label("last_activity"),
        )
        .join(User, User.id == AuditLog.actor_user_id, isouter=True)
        .where(AuditLog.organization_id == organization_id)
        .group_by(AuditLog.actor_user_id, User.full_name, User.email)
        .order_by(func.max(AuditLog.created_at).desc())
    ).all()
    return [
        {
            "actor_user_id": row.actor_user_id,
            "full_name": row.full_name,
            "email": row.email,
            "event_count": row.event_count,
            "last_activity": row.last_activity,
        }
        for row in rows
    ]
