import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, false, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    OfferApprovalStatus,
    OfferCurrency,
    OfferEmploymentType,
    OfferPayType,
    OfferStatus,
    OfferTaxTerm,
    RoleName,
)
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.job import Job
from app.db.models.offer import Offer, OfferApproval, OfferVersion
from app.schemas.auth import CurrentUser


def _scope_filter(query, viewer: CurrentUser | None):
    if viewer is None:
        return query
    scopes = scoped_roles(viewer.roles)
    if not scopes:
        return query

    # Interviewer has no OFFER permission at all, so only Hiring Manager scoping applies here.
    if RoleName.HIRING_MANAGER.value not in scopes:
        return query.where(false())

    return query.where(
        Offer.application_id.in_(
            select(Application.id).join(Job, Job.id == Application.job_id).where(Job.hiring_manager_id == viewer.id)
        )
    )


def _load(query):
    return query.options(selectinload(Offer.versions), selectinload(Offer.approvals))


# The compensation terms an offer carries, and each version snapshots.
_TERMS = (
    "pay_type",
    "base_salary",
    "hourly_rate",
    "currency",
    "employment_type",
    "tax_term",
    "contract_duration",
    "bonus",
    "equity",
    "joining_date",
)


def _one_of(label: str, value: str | None, choices: type) -> None:
    allowed = [c.value for c in choices]
    if value is not None and value not in allowed:
        raise ValidationAppError(f"{label} must be one of: {', '.join(allowed)}")


def _normalize_terms(offer: Offer) -> None:
    """Checks the terms hang together: a salaried offer needs a base salary and
    an hourly one an hourly rate, and the pay field the type does not use is
    cleared so a switch from salary to hourly leaves no stale figure behind."""
    _one_of("Pay type", offer.pay_type, OfferPayType)
    _one_of("Currency", offer.currency, OfferCurrency)
    _one_of("Employment type", offer.employment_type, OfferEmploymentType)
    _one_of("Employment terms", offer.tax_term, OfferTaxTerm)
    if offer.pay_type == OfferPayType.HOURLY.value:
        if offer.hourly_rate is None:
            raise ValidationAppError("An hourly offer needs an hourly rate")
        offer.base_salary = None
    else:
        if offer.base_salary is None:
            raise ValidationAppError("A salaried offer needs a base salary")
        offer.hourly_rate = None


def _snapshot(offer: Offer, version_number: int, actor_id: uuid.UUID | None) -> OfferVersion:
    return OfferVersion(
        offer_id=offer.id,
        version_number=version_number,
        created_by=actor_id,
        created_at=datetime.now(UTC),
        **{term: getattr(offer, term) for term in _TERMS},
    )


def create_offer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    application_id: uuid.UUID,
    **terms,
) -> Offer:
    application = db.get(Application, application_id)
    if application is None or application.organization_id != organization_id:
        raise NotFoundError("Application not found")

    offer = Offer(
        organization_id=organization_id,
        application_id=application_id,
        status=OfferStatus.DRAFT.value,
        created_by=actor_id,
        updated_by=actor_id,
        **{term: terms.get(term) for term in _TERMS if term in terms},
    )
    offer.pay_type = offer.pay_type or OfferPayType.SALARY.value
    offer.currency = offer.currency or OfferCurrency.USD.value
    _normalize_terms(offer)
    db.add(offer)
    db.flush()
    db.add(_snapshot(offer, 1, actor_id))
    db.commit()
    db.refresh(offer)
    return offer


def get_offer(db: Session, organization_id: uuid.UUID, offer_id: uuid.UUID, *, viewer: CurrentUser | None = None) -> Offer:
    query = _load(select(Offer)).where(Offer.id == offer_id, Offer.organization_id == organization_id)
    offer = db.scalar(_scope_filter(query, viewer))
    if offer is None:
        raise NotFoundError("Offer not found")
    return offer


def build_offers_query(
    organization_id: uuid.UUID,
    *,
    application_id: uuid.UUID | None = None,
    status: str | None = None,
    viewer: CurrentUser | None = None,
) -> Select:
    """Filtered, scoped, newest-first offer query; the caller pages it."""
    query = _load(select(Offer)).where(Offer.organization_id == organization_id)
    if application_id is not None:
        query = query.where(Offer.application_id == application_id)
    if status is not None:
        query = query.where(Offer.status == status)
    query = _scope_filter(query, viewer)
    return query.order_by(Offer.created_at.desc(), Offer.id)


_FINISHED_OFFER_STATUSES = (OfferStatus.ACCEPTED.value, OfferStatus.DECLINED.value, OfferStatus.EXPIRED.value)


def offer_summary(db: Session, organization_id: uuid.UUID, *, viewer: CurrentUser | None = None) -> dict[str, int]:
    """Counts for the list page's stat cards, within the viewer's scope."""
    query = select(
        func.count(Offer.id).filter(Offer.status.not_in(_FINISHED_OFFER_STATUSES)),
        func.count(Offer.id).filter(Offer.status == OfferStatus.APPROVAL_PENDING.value),
        func.count(Offer.id).filter(Offer.status == OfferStatus.SENT.value),
        func.count(Offer.id).filter(Offer.status == OfferStatus.ACCEPTED.value),
    ).where(Offer.organization_id == organization_id)
    in_progress, awaiting, sent, accepted = db.execute(_scope_filter(query, viewer)).one()
    return {"in_progress": in_progress, "awaiting_approval": awaiting, "sent": sent, "accepted": accepted}


def update_offer(db: Session, offer: Offer, *, actor_id: uuid.UUID | None, **fields) -> Offer:
    if offer.status != OfferStatus.DRAFT.value:
        raise ValidationAppError("Only draft offers can be edited")

    for key, value in fields.items():
        # pay_type and currency always have a value; the rest may be cleared.
        if value is not None or key not in ("pay_type", "currency"):
            setattr(offer, key, value)
    _normalize_terms(offer)
    offer.updated_by = actor_id
    db.flush()

    next_version = (max((v.version_number for v in offer.versions), default=0)) + 1
    db.add(_snapshot(offer, next_version, actor_id))
    db.commit()
    db.refresh(offer)
    return offer


def submit_for_approval(db: Session, offer: Offer, *, actor_id: uuid.UUID | None, note: str | None) -> Offer:
    if offer.status != OfferStatus.DRAFT.value:
        raise ValidationAppError("Only draft offers can be submitted for approval")

    offer.status = OfferStatus.APPROVAL_PENDING.value
    db.add(
        OfferApproval(
            offer_id=offer.id,
            requested_by=actor_id,
            status=OfferApprovalStatus.PENDING.value,
            note=note,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.refresh(offer)
    return offer


def _latest_approval(offer: Offer) -> OfferApproval | None:
    return offer.approvals[-1] if offer.approvals else None


def approve_offer(db: Session, offer: Offer, *, approver_id: uuid.UUID | None, note: str | None) -> Offer:
    approval = _latest_approval(offer)
    if (
        offer.status != OfferStatus.APPROVAL_PENDING.value
        or approval is None
        or approval.status != OfferApprovalStatus.PENDING.value
    ):
        raise ValidationAppError("Offer has no pending approval request")

    approval.status = OfferApprovalStatus.APPROVED.value
    approval.approver_id = approver_id
    approval.note = note or approval.note
    approval.decided_at = datetime.now(UTC)
    db.commit()
    db.refresh(offer)
    return offer


def reject_offer(db: Session, offer: Offer, *, approver_id: uuid.UUID | None, note: str | None) -> Offer:
    approval = _latest_approval(offer)
    if (
        offer.status != OfferStatus.APPROVAL_PENDING.value
        or approval is None
        or approval.status != OfferApprovalStatus.PENDING.value
    ):
        raise ValidationAppError("Offer has no pending approval request")

    approval.status = OfferApprovalStatus.REJECTED.value
    approval.approver_id = approver_id
    approval.note = note or approval.note
    approval.decided_at = datetime.now(UTC)
    offer.status = OfferStatus.DRAFT.value
    db.commit()
    db.refresh(offer)
    return offer


def send_offer(db: Session, offer: Offer) -> Offer:
    approval = _latest_approval(offer)
    if (
        offer.status != OfferStatus.APPROVAL_PENDING.value
        or approval is None
        or approval.status != OfferApprovalStatus.APPROVED.value
    ):
        raise ValidationAppError("Offer must be approved before it can be sent")

    offer.status = OfferStatus.SENT.value
    db.commit()
    db.refresh(offer)
    return offer


def mark_accepted(db: Session, offer: Offer, *, actor_id: uuid.UUID | None = None) -> Offer:
    if offer.status != OfferStatus.SENT.value:
        raise ValidationAppError("Only sent offers can be marked accepted")
    offer.status = OfferStatus.ACCEPTED.value

    # Auto-open an onboarding case so the hire journey continues past acceptance.
    # Imported locally to avoid a circular import between the offer and onboarding services.
    from app.services.onboarding import service as onboarding_service

    onboarding_service.open_case_for_offer(db, offer, actor_id=actor_id)

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
