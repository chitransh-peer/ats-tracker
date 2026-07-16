import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.vendor import VendorContactCreate, VendorCreate, VendorRead, VendorUpdate
from app.services.vendors import service as vendor_service

router = APIRouter(prefix="/vendors", tags=["vendors"])


def _to_read(db: Session, vendor) -> VendorRead:
    return VendorRead(
        id=vendor.id,
        organization_id=vendor.organization_id,
        name=vendor.name,
        specialization=vendor.specialization,
        status=vendor.status,
        contacts=vendor.contacts,
        active_submissions=vendor_service.active_submissions_count(db, vendor.organization_id, vendor.name),
    )


@router.get("", response_model=list[VendorRead])
def list_vendors(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.VENDOR, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[VendorRead]:
    vendors = vendor_service.list_vendors(db, current_user.organization_id)
    return [_to_read(db, v) for v in vendors]


@router.post("", response_model=VendorRead, status_code=201)
def create_vendor(
    payload: VendorCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.VENDOR, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.create_vendor(
        db,
        organization_id=current_user.organization_id,
        name=payload.name,
        specialization=payload.specialization,
        status=payload.status,
    )
    return _to_read(db, vendor)


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(
    vendor_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.VENDOR, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    return _to_read(db, vendor)


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.VENDOR, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    vendor = vendor_service.update_vendor(db, vendor, **payload.model_dump(exclude_unset=True))
    return _to_read(db, vendor)


@router.post("/{vendor_id}/contacts", response_model=VendorRead, status_code=201)
def add_vendor_contact(
    vendor_id: uuid.UUID,
    payload: VendorContactCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.VENDOR, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    vendor_service.add_contact(db, vendor, name=payload.name, email=payload.email, phone=payload.phone)
    db.refresh(vendor)
    return _to_read(db, vendor)
