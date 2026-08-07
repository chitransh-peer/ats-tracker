import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.vendor import (
    VendorAccountCreate,
    VendorAccountRead,
    VendorBankAccountCreate,
    VendorBankAccountRead,
    VendorContactCreate,
    VendorContactRead,
    VendorCreate,
    VendorDocumentRead,
    VendorMeetingCreate,
    VendorMeetingRead,
    VendorNoteCreate,
    VendorNoteRead,
    VendorRead,
    VendorUpdate,
)
from app.services.vendors import service as vendor_service

router = APIRouter(prefix="/vendors", tags=["vendors"])

_READ = require_permission(PermissionResource.VENDOR, PermissionAction.READ)
_CREATE = require_permission(PermissionResource.VENDOR, PermissionAction.CREATE)
_UPDATE = require_permission(PermissionResource.VENDOR, PermissionAction.UPDATE)


def _contact_read(contact) -> VendorContactRead:
    return VendorContactRead(
        id=contact.id,
        name=contact.name,
        email=contact.email,
        phone=contact.phone,
        work_phone=contact.work_phone,
        designation=contact.designation,
        status=contact.status,
        vms_status=contact.vms_status,
        owner_id=contact.owner_id,
        owner_name=contact.owner.full_name if contact.owner else None,
    )


def _to_read(db: Session, vendor) -> VendorRead:
    return VendorRead(
        **{
            column.name: getattr(vendor, column.name)
            for column in vendor.__table__.columns
            if column.name not in {"created_by", "updated_by"}
        },
        created_by=vendor.created_by,
        updated_by=vendor.updated_by,
        primary_owner_name=vendor.primary_owner.full_name if vendor.primary_owner else None,
        ownership_name=vendor.ownership.full_name if vendor.ownership else None,
        vendor_lead_name=vendor.vendor_lead.full_name if vendor.vendor_lead else None,
        created_by_name=vendor.created_by_user.full_name if vendor.created_by_user else None,
        updated_by_name=vendor.updated_by_user.full_name if vendor.updated_by_user else None,
        contacts=[_contact_read(c) for c in vendor.contacts],
        accounts=vendor.accounts,
        bank_accounts=vendor.bank_accounts,
        active_submissions=vendor_service.active_submissions_count(
            db, vendor.organization_id, vendor.name
        ),
    )


def _note_read(note, names: dict[uuid.UUID, str]) -> VendorNoteRead:
    return VendorNoteRead(
        id=note.id,
        body=note.body,
        action=note.action,
        author_id=note.author_id,
        author_name=note.author.full_name if note.author else None,
        notified_user_ids=note.notified_user_ids,
        notified_people=[names[uid] for uid in note.notified_user_ids if uid in names],
        created_at=note.created_at,
    )


def _meeting_read(meeting, names: dict[uuid.UUID, str]) -> VendorMeetingRead:
    return VendorMeetingRead(
        id=meeting.id,
        meeting_for=meeting.meeting_for,
        description=meeting.description,
        contact_id=meeting.contact_id,
        contact_name=meeting.contact.name if meeting.contact else None,
        attendee_ids=meeting.attendee_ids,
        attendee_names=[names[uid] for uid in meeting.attendee_ids if uid in names],
        guest_attendees=meeting.guest_attendees,
        start_time=meeting.start_time,
        duration_minutes=meeting.duration_minutes,
        created_by_id=meeting.created_by_id,
        created_by_name=meeting.creator.full_name if meeting.creator else None,
    )


@router.get("", response_model=list[VendorRead])
def list_vendors(
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[VendorRead]:
    vendors = vendor_service.list_vendors(db, current_user.organization_id)
    return [_to_read(db, v) for v in vendors]


@router.post("", response_model=VendorRead, status_code=201)
def create_vendor(
    payload: VendorCreate,
    current_user: CurrentUser = Depends(_CREATE),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    data = payload.model_dump()
    vendor = vendor_service.create_vendor(
        db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        accounts=data.pop("accounts", []),
        contacts=data.pop("contacts", []),
        notes=data.pop("notes", []),
        bank_accounts=data.pop("bank_accounts", []),
        **data,
    )
    return _to_read(db, vendor)


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(
    vendor_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    return _to_read(db, vendor)


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    vendor_service.update_vendor(
        db, vendor, actor_id=current_user.id, **payload.model_dump(exclude_unset=True)
    )
    return _to_read(db, vendor_service.get_vendor(db, current_user.organization_id, vendor_id))


@router.post("/{vendor_id}/contacts", response_model=VendorRead, status_code=201)
def add_vendor_contact(
    vendor_id: uuid.UUID,
    payload: VendorContactCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    vendor_service.add_contact(db, vendor, **payload.model_dump())
    return _to_read(db, vendor_service.get_vendor(db, current_user.organization_id, vendor_id))


@router.post("/{vendor_id}/accounts", response_model=VendorAccountRead, status_code=201)
def add_vendor_account(
    vendor_id: uuid.UUID,
    payload: VendorAccountCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorAccountRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    return vendor_service.add_account(db, vendor, **payload.model_dump())


@router.post("/{vendor_id}/bank-accounts", response_model=VendorBankAccountRead, status_code=201)
def add_vendor_bank_account(
    vendor_id: uuid.UUID,
    payload: VendorBankAccountCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorBankAccountRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    return vendor_service.add_bank_account(db, vendor, **payload.model_dump())


@router.get("/{vendor_id}/notes", response_model=list[VendorNoteRead])
def list_vendor_notes(
    vendor_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[VendorNoteRead]:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    notes = vendor_service.list_notes(db, vendor)
    names = vendor_service.resolve_user_names(
        db, [uid for n in notes for uid in n.notified_user_ids]
    )
    return [_note_read(n, names) for n in notes]


@router.post("/{vendor_id}/notes", response_model=VendorNoteRead, status_code=201)
def add_vendor_note(
    vendor_id: uuid.UUID,
    payload: VendorNoteCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorNoteRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    note = vendor_service.add_note(db, vendor, author_id=current_user.id, **payload.model_dump())
    names = vendor_service.resolve_user_names(db, note.notified_user_ids)
    return _note_read(note, names)


@router.get("/{vendor_id}/meetings", response_model=list[VendorMeetingRead])
def list_vendor_meetings(
    vendor_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[VendorMeetingRead]:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    meetings = vendor_service.list_meetings(db, vendor)
    names = vendor_service.resolve_user_names(db, [uid for m in meetings for uid in m.attendee_ids])
    return [_meeting_read(m, names) for m in meetings]


@router.post("/{vendor_id}/meetings", response_model=VendorMeetingRead, status_code=201)
def add_vendor_meeting(
    vendor_id: uuid.UUID,
    payload: VendorMeetingCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorMeetingRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    meeting = vendor_service.add_meeting(
        db, vendor, created_by_id=current_user.id, **payload.model_dump()
    )
    names = vendor_service.resolve_user_names(db, meeting.attendee_ids)
    return _meeting_read(meeting, names)


@router.get("/{vendor_id}/documents", response_model=list[VendorDocumentRead])
def list_vendor_documents(
    vendor_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[VendorDocumentRead]:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    return vendor_service.list_documents(db, vendor)


@router.post("/{vendor_id}/documents", response_model=VendorDocumentRead, status_code=201)
async def upload_vendor_document(
    vendor_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> VendorDocumentRead:
    vendor = vendor_service.get_vendor(db, current_user.organization_id, vendor_id)
    data = await file.read()
    return vendor_service.add_document(
        db,
        vendor,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        uploaded_by=current_user.id,
    )
