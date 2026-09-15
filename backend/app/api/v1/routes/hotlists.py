import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.core.exceptions import ValidationAppError
from app.schemas.auth import CurrentUser
from app.schemas.hotlist import (
    AddPartyRecipientsRequest,
    AddRecipientsRequest,
    HotlistCreate,
    HotlistListItem,
    HotlistMemberRead,
    HotlistRead,
    HotlistRecipientRead,
    HotlistSendRead,
    HotlistUpdate,
    RecipientImportResult,
    SetMembersRequest,
)
from app.services.audit.service import record as record_audit
from app.services.hotlist import service as hotlist_service
from app.services.hotlist.spreadsheet import (
    build_hotlist_workbook,
    build_recipient_template_workbook,
)
from app.workers.tasks.mail import send_hotlist_task

router = APIRouter(prefix="/hotlists", tags=["hotlists"])

_read = require_permission(PermissionResource.HOTLIST, PermissionAction.READ)
_create = require_permission(PermissionResource.HOTLIST, PermissionAction.CREATE)
_update = require_permission(PermissionResource.HOTLIST, PermissionAction.UPDATE)
_delete = require_permission(PermissionResource.HOTLIST, PermissionAction.DELETE)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Recipient sheets are contact lists, not archives; anything larger is a mistake.
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _member_read(member) -> HotlistMemberRead:
    profile = member.bench_profile
    return HotlistMemberRead(
        id=member.id,
        bench_profile_id=member.bench_profile_id,
        sort_order=member.sort_order,
        headline_override=member.headline_override,
        full_name=profile.candidate.full_name,
        email=profile.candidate.email,
        marketing_title=member.headline_override or profile.marketing_title or profile.candidate.current_title,
        work_auth=profile.candidate.work_auth,
        bench_age_days=profile.bench_age_days,
    )


def _to_read(hotlist) -> HotlistRead:
    return HotlistRead(
        id=hotlist.id,
        organization_id=hotlist.organization_id,
        name=hotlist.name,
        status=hotlist.status,
        template_id=hotlist.template_id,
        subject=hotlist.subject,
        body=hotlist.body,
        attach_spreadsheet=hotlist.attach_spreadsheet,
        include_rates=hotlist.include_rates,
        include_candidate_contact=hotlist.include_candidate_contact,
        notes=hotlist.notes,
        members=[_member_read(m) for m in sorted(hotlist.members, key=lambda m: m.sort_order)],
        recipients=[HotlistRecipientRead.model_validate(r) for r in hotlist.recipients],
        created_at=hotlist.created_at,
        updated_at=hotlist.updated_at,
    )


@router.get("", response_model=list[HotlistListItem])
def list_hotlists(
    status: str | None = None,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> list[HotlistListItem]:
    return [
        HotlistListItem(
            id=h.id,
            name=h.name,
            status=h.status,
            subject=h.subject,
            member_count=len(h.members),
            recipient_count=len(h.recipients),
            created_at=h.created_at,
            updated_at=h.updated_at,
        )
        for h in hotlist_service.list_hotlists(db, current_user.organization_id, status=status)
    ]


@router.get("/recipient-template", response_class=Response)
def download_recipient_template(_current_user: CurrentUser = Depends(_read)) -> Response:
    """A blank sheet to fill in and upload back as a recipient list."""
    return Response(
        content=build_recipient_template_workbook(),
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": 'attachment; filename="hotlist-recipients-template.xlsx"'},
    )


@router.get("/suggested-members", response_model=list[uuid.UUID])
def suggested_members(current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)) -> list[uuid.UUID]:
    """Bench profiles worth adding — longest on the bench first."""
    profiles = hotlist_service.suggest_members(db, current_user.organization_id, viewer=current_user)
    return [p.id for p in profiles]


@router.get("/{hotlist_id}", response_model=HotlistRead)
def get_hotlist(
    hotlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> HotlistRead:
    return _to_read(hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id))


@router.post("", response_model=HotlistRead, status_code=201)
def create_hotlist(
    payload: HotlistCreate,
    current_user: CurrentUser = Depends(_create),
    db: Session = Depends(get_db_session),
) -> HotlistRead:
    data = payload.model_dump(exclude_unset=True)
    hotlist = hotlist_service.create_hotlist(
        db, organization_id=current_user.organization_id, actor_id=current_user.id, **data
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.HOTLIST_CREATED.value,
        resource_type="hotlist",
        resource_id=str(hotlist.id),
        metadata={"name": hotlist.name},
    )
    db.commit()
    db.refresh(hotlist)
    return _to_read(hotlist)


@router.patch("/{hotlist_id}", response_model=HotlistRead)
def update_hotlist(
    hotlist_id: uuid.UUID,
    payload: HotlistUpdate,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> HotlistRead:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    data = payload.model_dump(exclude_unset=True)
    hotlist = hotlist_service.update_hotlist(db, hotlist, actor_id=current_user.id, **data)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.HOTLIST_UPDATED.value,
        resource_type="hotlist",
        resource_id=str(hotlist.id),
        metadata={"changed": sorted(data.keys())},
    )
    db.commit()
    db.refresh(hotlist)
    return _to_read(hotlist)


@router.delete("/{hotlist_id}", status_code=204)
def delete_hotlist(
    hotlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(_delete),
    db: Session = Depends(get_db_session),
) -> None:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    hotlist_service.delete_hotlist(db, hotlist)


# --------------------------------------------------------------------- members


@router.put("/{hotlist_id}/members", response_model=HotlistRead)
def set_members(
    hotlist_id: uuid.UUID,
    payload: SetMembersRequest,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> HotlistRead:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    hotlist = hotlist_service.set_members(db, hotlist, payload.bench_profile_ids, viewer=current_user)
    return _to_read(hotlist)


# ------------------------------------------------------------------ recipients


@router.post("/{hotlist_id}/recipients", response_model=HotlistRead, status_code=201)
def add_recipients(
    hotlist_id: uuid.UUID,
    payload: AddRecipientsRequest,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> HotlistRead:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    hotlist_service.add_manual_recipients(db, hotlist, [r.model_dump() for r in payload.recipients])
    db.refresh(hotlist)
    return _to_read(hotlist)


@router.post("/{hotlist_id}/recipients/from-parties", response_model=HotlistRead, status_code=201)
def add_party_recipients(
    hotlist_id: uuid.UUID,
    payload: AddPartyRecipientsRequest,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> HotlistRead:
    """Add every known contact address for the given clients and vendors."""
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    if payload.client_ids:
        hotlist_service.add_client_recipients(db, hotlist, payload.client_ids)
    if payload.vendor_ids:
        hotlist_service.add_vendor_recipients(db, hotlist, payload.vendor_ids)
    db.refresh(hotlist)
    return _to_read(hotlist)


@router.post("/{hotlist_id}/recipients/import", response_model=RecipientImportResult)
async def import_recipients(
    hotlist_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> RecipientImportResult:
    """Bulk-load recipients from an .xlsx of first name / last name / email."""
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)

    data = await file.read()
    if not data:
        raise ValidationAppError("The uploaded file is empty.")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise ValidationAppError("The file is larger than 5 MB. Recipient lists should be well under that.")

    result = hotlist_service.import_recipients_from_workbook(db, hotlist, data)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.HOTLIST_RECIPIENTS_IMPORTED.value,
        resource_type="hotlist",
        resource_id=str(hotlist.id),
        metadata={"added": result["added"], "skipped": result["skipped"], "file_name": file.filename},
    )
    db.commit()
    return RecipientImportResult(**result)


@router.delete("/{hotlist_id}/recipients/{recipient_id}", status_code=204)
def remove_recipient(
    hotlist_id: uuid.UUID,
    recipient_id: uuid.UUID,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> None:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    hotlist_service.remove_recipient(db, hotlist, recipient_id)


@router.post("/{hotlist_id}/recipients/{recipient_id}/unsubscribe", response_model=HotlistRecipientRead)
def unsubscribe_recipient(
    hotlist_id: uuid.UUID,
    recipient_id: uuid.UUID,
    unsubscribed: bool = True,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> HotlistRecipientRead:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    return hotlist_service.set_recipient_unsubscribed(db, hotlist, recipient_id, unsubscribed)


# ------------------------------------------------------------ export and send


@router.get("/{hotlist_id}/export", response_class=Response)
def export_hotlist(
    hotlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> Response:
    """Download the consultant sheet — the same file that gets attached."""
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    workbook = build_hotlist_workbook(
        hotlist_name=hotlist.name,
        profiles=sorted(hotlist.members, key=lambda m: m.sort_order),
        include_rates=hotlist.include_rates,
        include_candidate_contact=hotlist.include_candidate_contact,
    )
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "-" for c in hotlist.name).strip() or "hotlist"
    return Response(
        content=workbook,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.xlsx"'},
    )


@router.get("/{hotlist_id}/sends", response_model=list[HotlistSendRead])
def list_sends(
    hotlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> list[HotlistSendRead]:
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    return hotlist_service.list_sends(db, hotlist)


@router.post("/{hotlist_id}/send", response_model=HotlistSendRead, status_code=202)
def send_hotlist(
    hotlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> HotlistSendRead:
    """Queue the hotlist for delivery to every subscribed recipient."""
    hotlist = hotlist_service.get_hotlist(db, current_user.organization_id, hotlist_id)
    send = hotlist_service.create_send(db, hotlist, actor_id=current_user.id)

    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.HOTLIST_SENT.value,
        resource_type="hotlist",
        resource_id=str(hotlist.id),
        metadata={
            "send_id": str(send.id),
            "members": send.member_count,
            "recipients": send.recipient_count,
        },
    )
    db.commit()

    # Handed to the worker: a 200-address batch must not block the request, and
    # each address needs its own recorded outcome.
    send_hotlist_task.send(str(send.id))
    db.refresh(send)
    return send
