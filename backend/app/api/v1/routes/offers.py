import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.offer import OfferApprovalDecision, OfferCreate, OfferRead, OfferUpdate
from app.services.audit.service import record as record_audit
from app.services.offers import service as offer_service

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_model=list[OfferRead])
def list_offers(
    application_id: uuid.UUID | None = None,
    status: str | None = None,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[OfferRead]:
    return offer_service.list_offers(
        db, current_user.organization_id, application_id=application_id, status=status, viewer=current_user
    )


@router.post("", response_model=OfferRead, status_code=201)
def create_offer(
    payload: OfferCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.create_offer(
        db, organization_id=current_user.organization_id, actor_id=current_user.id, **payload.model_dump()
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.OFFER_CREATED.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.get("/{offer_id}", response_model=OfferRead)
def get_offer(
    offer_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    return offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)


@router.patch("/{offer_id}", response_model=OfferRead)
def update_offer(
    offer_id: uuid.UUID,
    payload: OfferUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    offer = offer_service.update_offer(db, offer, actor_id=current_user.id, **payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.OFFER_UPDATED.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.post("/{offer_id}/submit-approval", response_model=OfferRead)
def submit_approval(
    offer_id: uuid.UUID,
    payload: OfferApprovalDecision,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    offer = offer_service.submit_for_approval(db, offer, actor_id=current_user.id, note=payload.note)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.OFFER_SUBMITTED_FOR_APPROVAL.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.post("/{offer_id}/approve", response_model=OfferRead)
def approve_offer(
    offer_id: uuid.UUID,
    payload: OfferApprovalDecision,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.MANAGE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    offer = offer_service.approve_offer(db, offer, approver_id=current_user.id, note=payload.note)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.OFFER_APPROVED.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.post("/{offer_id}/reject", response_model=OfferRead)
def reject_offer(
    offer_id: uuid.UUID,
    payload: OfferApprovalDecision,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.MANAGE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    offer = offer_service.reject_offer(db, offer, approver_id=current_user.id, note=payload.note)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.OFFER_REJECTED.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.post("/{offer_id}/send", response_model=OfferRead)
def send_offer(
    offer_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    offer = offer_service.send_offer(db, offer)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.OFFER_SENT.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.post("/{offer_id}/accept", response_model=OfferRead)
def accept_offer(
    offer_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    offer = offer_service.mark_accepted(db, offer, actor_id=current_user.id)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.ONBOARDING_CASE_OPENED.value,
        resource_type="offer",
        resource_id=str(offer.id),
    )
    db.commit()
    return offer


@router.post("/{offer_id}/decline", response_model=OfferRead)
def decline_offer(
    offer_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    return offer_service.mark_declined(db, offer)


@router.post("/{offer_id}/expire", response_model=OfferRead)
def expire_offer(
    offer_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.OFFER, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OfferRead:
    offer = offer_service.get_offer(db, current_user.organization_id, offer_id, viewer=current_user)
    return offer_service.mark_expired(db, offer)
