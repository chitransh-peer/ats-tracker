import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import VendorStatus
from app.core.exceptions import NotFoundError
from app.db.models.application import Application
from app.db.models.user import User
from app.db.models.vendor import (
    Vendor,
    VendorAccount,
    VendorBankAccount,
    VendorContact,
    VendorDocument,
    VendorMeeting,
    VendorNote,
)
from app.services.storage import service as storage_service

_LOAD_OPTIONS = (
    selectinload(Vendor.contacts).selectinload(VendorContact.owner),
    selectinload(Vendor.accounts),
    selectinload(Vendor.bank_accounts),
    selectinload(Vendor.primary_owner),
    selectinload(Vendor.ownership),
    selectinload(Vendor.vendor_lead),
    selectinload(Vendor.created_by_user),
    selectinload(Vendor.updated_by_user),
)


def _search_filter(search: str | None):
    """Case-insensitive "contains" across the fields the list's search box
    promises. Backed by trigram indexes, so it stays fast at 50,000 vendors."""
    if not search or not search.strip():
        return None
    like = f"%{search.strip()}%"
    return or_(Vendor.name.ilike(like), Vendor.state.ilike(like), Vendor.country.ilike(like))


def build_vendors_query(organization_id: uuid.UUID, *, search: str | None = None, status: str | None = None) -> Select:
    """Filtered, ordered vendor query for one page of the list; the caller
    pages it (app/core/pagination.py)."""
    query = select(Vendor).where(Vendor.organization_id == organization_id)
    condition = _search_filter(search)
    if condition is not None:
        query = query.where(condition)
    if status:
        query = query.where(Vendor.status == status)
    return query.options(*_LOAD_OPTIONS).order_by(Vendor.created_at.desc(), Vendor.id)


def list_vendors(db: Session, organization_id: uuid.UUID) -> list[Vendor]:
    return list(db.scalars(build_vendors_query(organization_id)).all())


def vendor_summary(db: Session, organization_id: uuid.UUID) -> dict:
    """The list page's headline counts, computed by the database rather than
    by loading every vendor to count them in the browser."""
    row = db.execute(
        select(
            func.count(Vendor.id),
            func.count(Vendor.id).filter(Vendor.status == VendorStatus.ACTIVE.value),
            func.count(Vendor.id).filter(Vendor.primary_vendor.is_(True)),
        ).where(Vendor.organization_id == organization_id)
    ).one()
    submissions = (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.organization_id == organization_id, Application.source.like("vendor:%")
            )
        )
        or 0
    )
    return {"total": row[0], "active": row[1], "primary": row[2], "active_submissions": submissions}


def vendor_options(
    db: Session,
    organization_id: uuid.UUID,
    *,
    search: str | None = None,
    ids: list[uuid.UUID] | None = None,
    limit: int = 20,
) -> list[tuple[uuid.UUID, str]]:
    """(id, name) pairs for a type-to-search picker: the first `limit` matches
    for `search`, or the named `ids` so a picker can label its current value."""
    query = select(Vendor.id, Vendor.name).where(Vendor.organization_id == organization_id)
    if ids:
        query = query.where(Vendor.id.in_(ids))
    else:
        condition = _search_filter(search)
        if condition is not None:
            query = query.where(condition)
    return [(r.id, r.name) for r in db.execute(query.order_by(Vendor.name).limit(limit)).all()]


def active_submissions_counts(db: Session, organization_id: uuid.UUID, vendor_names: list[str]) -> dict[str, int]:
    """`active_submissions_count` for a whole page of vendors in one query."""
    if not vendor_names:
        return {}
    tags = {f"vendor:{name}": name for name in vendor_names}
    rows = db.execute(
        select(Application.source, func.count(Application.id))
        .where(Application.organization_id == organization_id, Application.source.in_(list(tags)))
        .group_by(Application.source)
    ).all()
    return {tags[source]: count for source, count in rows}


def get_vendor(db: Session, organization_id: uuid.UUID, vendor_id: uuid.UUID) -> Vendor:
    vendor = db.scalar(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.organization_id == organization_id).options(*_LOAD_OPTIONS)
    )
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


def create_vendor(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    accounts: list[dict] | None = None,
    contacts: list[dict] | None = None,
    notes: list[dict] | None = None,
    bank_accounts: list[dict] | None = None,
    **fields,
) -> Vendor:
    vendor = Vendor(organization_id=organization_id, created_by=actor_id, updated_by=actor_id, **fields)
    db.add(vendor)
    db.flush()

    for account in accounts or []:
        db.add(VendorAccount(vendor_id=vendor.id, **account))
    for contact in contacts or []:
        db.add(VendorContact(vendor_id=vendor.id, **contact))
    for note in notes or []:
        db.add(VendorNote(vendor_id=vendor.id, author_id=actor_id, **note))
    for bank_account in bank_accounts or []:
        db.add(VendorBankAccount(vendor_id=vendor.id, **bank_account))

    db.commit()
    return get_vendor(db, organization_id, vendor.id)


def update_vendor(db: Session, vendor: Vendor, *, actor_id: uuid.UUID | None = None, **fields) -> Vendor:
    for key, value in fields.items():
        if value is not None:
            setattr(vendor, key, value)
    if actor_id is not None:
        vendor.updated_by = actor_id
    db.commit()
    db.refresh(vendor)
    return vendor


def add_contact(db: Session, vendor: Vendor, **fields) -> VendorContact:
    contact = VendorContact(vendor_id=vendor.id, **fields)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def add_account(db: Session, vendor: Vendor, **fields) -> VendorAccount:
    account = VendorAccount(vendor_id=vendor.id, **fields)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def add_bank_account(db: Session, vendor: Vendor, **fields) -> VendorBankAccount:
    bank_account = VendorBankAccount(vendor_id=vendor.id, **fields)
    db.add(bank_account)
    db.commit()
    db.refresh(bank_account)
    return bank_account


def add_note(db: Session, vendor: Vendor, *, author_id: uuid.UUID | None, **fields) -> VendorNote:
    note = VendorNote(vendor_id=vendor.id, author_id=author_id, **fields)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, vendor: Vendor) -> list[VendorNote]:
    return list(
        db.scalars(
            select(VendorNote)
            .where(VendorNote.vendor_id == vendor.id)
            .options(selectinload(VendorNote.author))
            .order_by(VendorNote.created_at.desc())
        ).all()
    )


def add_meeting(db: Session, vendor: Vendor, *, created_by_id: uuid.UUID | None, **fields) -> VendorMeeting:
    meeting = VendorMeeting(vendor_id=vendor.id, created_by_id=created_by_id, **fields)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


def list_meetings(db: Session, vendor: Vendor) -> list[VendorMeeting]:
    return list(
        db.scalars(
            select(VendorMeeting)
            .where(VendorMeeting.vendor_id == vendor.id)
            .options(selectinload(VendorMeeting.contact), selectinload(VendorMeeting.creator))
            .order_by(VendorMeeting.start_time.desc().nullslast())
        ).all()
    )


def add_document(
    db: Session,
    vendor: Vendor,
    *,
    file_name: str,
    content_type: str,
    data: bytes,
    uploaded_by: uuid.UUID | None,
) -> VendorDocument:
    key = f"vendors/{vendor.id}/{uuid.uuid4()}-{file_name}"
    storage_service.upload_bytes(key, data, content_type)
    document = VendorDocument(
        vendor_id=vendor.id,
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(data),
        storage_key=key,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, vendor: Vendor, document_id: uuid.UUID) -> VendorDocument:
    """Fetch one document, scoped to the vendor it belongs to, so a document id
    cannot be used to reach a file hanging off a record the caller cannot see."""
    document = db.scalar(
        select(VendorDocument).where(
            VendorDocument.id == document_id,
            VendorDocument.vendor_id == vendor.id,
        )
    )
    if document is None:
        raise NotFoundError("Document not found")
    return document


def list_documents(db: Session, vendor: Vendor) -> list[VendorDocument]:
    return list(
        db.scalars(
            select(VendorDocument).where(VendorDocument.vendor_id == vendor.id).order_by(VendorDocument.created_at.desc())
        ).all()
    )


def resolve_user_names(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Look up display names for the ad-hoc user-id arrays on notes and meetings."""
    if not user_ids:
        return {}
    rows = db.execute(select(User.id, User.full_name).where(User.id.in_(set(user_ids)))).all()
    return {row[0]: row[1] for row in rows}


def active_submissions_count(db: Session, organization_id: uuid.UUID, vendor_name: str) -> int:
    """Submissions are applications whose `source` tags this vendor by name (the
    lightweight vendor model agreed for Phase 2 — no dedicated submission table)."""
    return (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.organization_id == organization_id, Application.source == f"vendor:{vendor_name}"
            )
        )
        or 0
    )
