import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import OfferApprovalStatus, OfferStatus
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.application import Application
from app.db.models.offer import Offer, OfferApproval, OfferVersion


def _load(query):
    return query.options(selectinload(Offer.versions), selectinload(Offer.approvals))


def create_offer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    application_id: uuid.UUID,
    base_salary: int,
    bonus: int | None,
    equity: str | None,
    joining_date: date | None,
) -> Offer:
    application = db.get(Application, application_id)
    if application is None or application.organization_id != organization_id:
        raise NotFoundError("Application not found")

    offer = Offer(
        organization_id=organization_id,
        application_id=application_id,
        status=OfferStatus.DRAFT.value,
        base_salary=base_salary,
        bonus=bonus,
        equity=equity,
        joining_date=joining_date,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(offer)
    db.flush()
    db.add(
        OfferVersion(
            offer_id=offer.id, version_number=1, base_salary=base_salary, bonus=bonus, equity=equity,
            joining_date=joining_date, created_by=actor_id, created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(offer)
    return offer


def get_offer(db: Session, organization_id: uuid.UUID, offer_id: uuid.UUID) -> Offer:
    offer = db.scalar(_load(select(Offer)).where(Offer.id == offer_id, Offer.organization_id == organization_id))
    if offer is None:
        raise NotFoundError("Offer not found")
    return offer


def list_offers(
    db: Session, organization_id: uuid.UUID, *, application_id: uuid.UUID | None = None, status: str | None = None
) -> list[Offer]:
    query = _load(select(Offer)).where(Offer.organization_id == organization_id)
    if application_id is not None:
        query = query.where(Offer.application_id == application_id)
    if status is not None:
        query = query.where(Offer.status == status)
    return list(db.scalars(query.order_by(Offer.created_at.desc())).all())


def update_offer(db: Session, offer: Offer, *, actor_id: uuid.UUID | None, **fields) -> Offer:
    if offer.status != OfferStatus.DRAFT.value:
        raise ValidationAppError("Only draft offers can be edited")

    for key, value in fields.items():
        if value is not None:
            setattr(offer, key, value)
    offer.updated_by = actor_id
    db.flush()

    next_version = (max((v.version_number for v in offer.versions), default=0)) + 1
    db.add(
        OfferVersion(
            offer_id=offer.id, version_number=next_version, base_salary=offer.base_salary, bonus=offer.bonus,
            equity=offer.equity, joining_date=offer.joining_date, created_by=actor_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(offer)
    return offer


def submit_for_approval(db: Session, offer: Offer, *, actor_id: uuid.UUID | None, note: str | None) -> Offer:
    if offer.status != OfferStatus.DRAFT.value:
        raise ValidationAppError("Only draft offers can be submitted for approval")

    offer.status = OfferStatus.APPROVAL_PENDING.value
    db.add(
        OfferApproval(
            offer_id=offer.id, requested_by=actor_id, status=OfferApprovalStatus.PENDING.value, note=note,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(offer)
    return offer


def _latest_approval(offer: Offer) -> OfferApproval | None:
    return offer.approvals[-1] if offer.approvals else None


def approve_offer(db: Session, offer: Offer, *, approver_id: uuid.UUID | None, note: str | None) -> Offer:
    approval = _latest_approval(offer)
    if offer.status != OfferStatus.APPROVAL_PENDING.value or approval is None or approval.status != OfferApprovalStatus.PENDING.value:
        raise ValidationAppError("Offer has no pending approval request")

    approval.status = OfferApprovalStatus.APPROVED.value
    approval.approver_id = approver_id
    approval.note = note or approval.note
    approval.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(offer)
    return offer


def reject_offer(db: Session, offer: Offer, *, approver_id: uuid.UUID | None, note: str | None) -> Offer:
    approval = _latest_approval(offer)
    if offer.status != OfferStatus.APPROVAL_PENDING.value or approval is None or approval.status != OfferApprovalStatus.PENDING.value:
        raise ValidationAppError("Offer has no pending approval request")

    approval.status = OfferApprovalStatus.REJECTED.value
    approval.approver_id = approver_id
    approval.note = note or approval.note
    approval.decided_at = datetime.now(timezone.utc)
    offer.status = OfferStatus.DRAFT.value
    db.commit()
    db.refresh(offer)
    return offer


def send_offer(db: Session, offer: Offer) -> Offer:
    approval = _latest_approval(offer)
    if offer.status != OfferStatus.APPROVAL_PENDING.value or approval is None or approval.status != OfferApprovalStatus.APPROVED.value:
        raise ValidationAppError("Offer must be approved before it can be sent")

    offer.status = OfferStatus.SENT.value
    db.commit()
    db.refresh(offer)
    return offer


def mark_accepted(db: Session, offer: Offer) -> Offer:
    if offer.status != OfferStatus.SENT.value:
        raise ValidationAppError("Only sent offers can be marked accepted")
    offer.status = OfferStatus.ACCEPTED.value
    db.commit()
    db.refresh(offer)
    return offer


def mark_declined(db: Session, offer: Offer) -> Offer:
    if offer.status != OfferStatus.SENT.value:
        raise ValidationAppError("Only sent offers can be marked declined")
    offer.status = OfferStatus.DECLINED.value
    db.commit()
    db.refresh(offer)
    return offer


def mark_expired(db: Session, offer: Offer) -> Offer:
    if offer.status != OfferStatus.SENT.value:
        raise ValidationAppError("Only sent offers can be marked expired")
    offer.status = OfferStatus.EXPIRED.value
    db.commit()
    db.refresh(offer)
    return offer
