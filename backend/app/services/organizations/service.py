import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models.organization import Organization


def get_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    org = db.scalar(
        select(Organization).where(Organization.id == organization_id).options(selectinload(Organization.settings))
    )
    if org is None:
        raise NotFoundError("Organization not found")
    return org


def update_settings(db: Session, organization: Organization, **fields) -> Organization:
    for key, value in fields.items():
        if value is not None:
            setattr(organization.settings, key, value)
    db.commit()
    db.refresh(organization)
    return organization
