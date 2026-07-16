import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models.application import Application
from app.db.models.vendor import Vendor, VendorContact


def list_vendors(db: Session, organization_id: uuid.UUID) -> list[Vendor]:
    return list(
        db.scalars(
            select(Vendor).where(Vendor.organization_id == organization_id).options(selectinload(Vendor.contacts))
        ).all()
    )


def get_vendor(db: Session, organization_id: uuid.UUID, vendor_id: uuid.UUID) -> Vendor:
    vendor = db.scalar(
        select(Vendor)
        .where(Vendor.id == vendor_id, Vendor.organization_id == organization_id)
        .options(selectinload(Vendor.contacts))
    )
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


def create_vendor(
    db: Session, *, organization_id: uuid.UUID, name: str, specialization: str | None, status: str
) -> Vendor:
    vendor = Vendor(organization_id=organization_id, name=name, specialization=specialization, status=status)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def update_vendor(db: Session, vendor: Vendor, **fields) -> Vendor:
    for key, value in fields.items():
        if value is not None:
            setattr(vendor, key, value)
    db.commit()
    db.refresh(vendor)
    return vendor


def add_contact(db: Session, vendor: Vendor, *, name: str, email: str | None, phone: str | None) -> VendorContact:
    contact = VendorContact(vendor_id=vendor.id, name=name, email=email, phone=phone)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def active_submissions_count(db: Session, organization_id: uuid.UUID, vendor_name: str) -> int:
    """Submissions are applications whose `source` tags this vendor by name (the
    lightweight vendor model agreed for Phase 2 — no dedicated submission table)."""
    return db.scalar(
        select(func.count(Application.id)).where(
            Application.organization_id == organization_id, Application.source == f"vendor:{vendor_name}"
        )
    ) or 0
