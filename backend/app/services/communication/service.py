import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OutboundMessageStatus
from app.core.exceptions import NotFoundError
from app.db.models.communication import CommunicationTemplate, OutboundMessage


def create_template(
    db: Session, *, organization_id: uuid.UUID, actor_id: uuid.UUID | None, name: str, type: str, subject: str, body: str
) -> CommunicationTemplate:
    template = CommunicationTemplate(
        organization_id=organization_id, name=name, type=type, subject=subject, body=body, created_by=actor_id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def get_template(db: Session, organization_id: uuid.UUID, template_id: uuid.UUID) -> CommunicationTemplate:
    template = db.scalar(
        select(CommunicationTemplate).where(
            CommunicationTemplate.id == template_id, CommunicationTemplate.organization_id == organization_id
        )
    )
    if template is None:
        raise NotFoundError("Template not found")
    return template


def list_templates(db: Session, organization_id: uuid.UUID) -> list[CommunicationTemplate]:
    return list(
        db.scalars(
            select(CommunicationTemplate).where(CommunicationTemplate.organization_id == organization_id)
        ).all()
    )


def update_template(db: Session, template: CommunicationTemplate, **fields) -> CommunicationTemplate:
    for key, value in fields.items():
        if value is not None:
            setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


def log_message(
    db: Session,
    *,
    organization_id: uuid.UUID,
    sent_by: uuid.UUID | None,
    candidate_id: uuid.UUID | None,
    application_id: uuid.UUID | None,
    template_id: uuid.UUID | None,
    subject: str,
    body: str,
) -> OutboundMessage:
    """Records the message as sent in the candidate communication log. Does not
    perform real delivery — no email provider has been wired up yet (Phase 3 scope)."""
    message = OutboundMessage(
        organization_id=organization_id,
        candidate_id=candidate_id,
        application_id=application_id,
        template_id=template_id,
        sent_by=sent_by,
        subject=subject,
        body=body,
        status=OutboundMessageStatus.LOGGED.value,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_messages(
    db: Session, organization_id: uuid.UUID, *, candidate_id: uuid.UUID | None = None
) -> list[OutboundMessage]:
    query = select(OutboundMessage).where(OutboundMessage.organization_id == organization_id)
    if candidate_id is not None:
        query = query.where(OutboundMessage.candidate_id == candidate_id)
    return list(db.scalars(query.order_by(OutboundMessage.created_at.desc())).all())
