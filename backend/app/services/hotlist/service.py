"""Hotlist assembly and dispatch.

A hotlist is composed (members + recipients + covering email), then sent. The
send is handed to the background worker, because a list of 200 vendor addresses
must not block an HTTP request, and each address needs its own recorded outcome.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    HotlistRecipientKind,
    HotlistSendStatus,
    HotlistStatus,
    OutboundMessageStatus,
)
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.bench import BenchProfile
from app.db.models.client import Client, ClientAccount, ClientContact
from app.db.models.hotlist import (
    Hotlist,
    HotlistDelivery,
    HotlistMember,
    HotlistRecipient,
    HotlistSend,
)
from app.db.models.vendor import Vendor
from app.schemas.auth import CurrentUser
from app.services.bench import service as bench_service
from app.services.hotlist.spreadsheet import is_valid_email, parse_recipient_workbook


def _load(query):
    return query.options(
        selectinload(Hotlist.members).selectinload(HotlistMember.bench_profile).selectinload(BenchProfile.candidate),
        selectinload(Hotlist.recipients),
    )


def list_hotlists(db: Session, organization_id: uuid.UUID, *, status: str | None = None) -> list[Hotlist]:
    query = _load(select(Hotlist).where(Hotlist.organization_id == organization_id))
    if status:
        query = query.where(Hotlist.status == status)
    return list(db.scalars(query.order_by(Hotlist.created_at.desc())).unique().all())


def get_hotlist(db: Session, organization_id: uuid.UUID, hotlist_id: uuid.UUID) -> Hotlist:
    hotlist = (
        db.scalars(_load(select(Hotlist).where(Hotlist.id == hotlist_id, Hotlist.organization_id == organization_id)))
        .unique()
        .one_or_none()
    )
    if hotlist is None:
        raise NotFoundError("Hotlist not found")
    return hotlist


def create_hotlist(db: Session, *, organization_id: uuid.UUID, actor_id: uuid.UUID | None, name: str, **fields) -> Hotlist:
    hotlist = Hotlist(
        organization_id=organization_id,
        name=name,
        created_by=actor_id,
        updated_by=actor_id,
        **{k: v for k, v in fields.items() if v is not None},
    )
    db.add(hotlist)
    db.commit()
    db.refresh(hotlist)
    return hotlist


def update_hotlist(db: Session, hotlist: Hotlist, *, actor_id: uuid.UUID | None, **fields) -> Hotlist:
    for key, value in fields.items():
        if value is not None:
            setattr(hotlist, key, value)
    hotlist.updated_by = actor_id
    db.commit()
    db.refresh(hotlist)
    return hotlist


def delete_hotlist(db: Session, hotlist: Hotlist) -> None:
    db.delete(hotlist)
    db.commit()


# --------------------------------------------------------------------- members


def set_members(
    db: Session,
    hotlist: Hotlist,
    bench_profile_ids: list[uuid.UUID],
    *,
    viewer: CurrentUser | None = None,
) -> Hotlist:
    """Replace the consultant list.

    Profiles the viewer cannot see are dropped rather than rejected, so a
    recruiter cannot use hotlist membership to infer the existence of bench
    profiles outside their visibility.
    """
    visible = bench_service.get_profiles_by_ids(db, hotlist.organization_id, bench_profile_ids, viewer=viewer)
    allowed_ids = {p.id for p in visible}

    for row in list(hotlist.members):
        db.delete(row)
    db.flush()

    # Preserve the caller's ordering.
    for order, profile_id in enumerate([pid for pid in bench_profile_ids if pid in allowed_ids]):
        db.add(HotlistMember(hotlist_id=hotlist.id, bench_profile_id=profile_id, sort_order=order))

    db.commit()
    db.refresh(hotlist)
    return hotlist


# ------------------------------------------------------------------ recipients


def _add_recipients(db: Session, hotlist: Hotlist, records: list[dict], kind: str) -> tuple[int, int]:
    """Insert recipients, skipping addresses already on this hotlist."""
    existing = {r.email.lower() for r in hotlist.recipients}
    added = skipped = 0
    for record in records:
        email = (record.get("email") or "").strip().lower()
        if not email or not is_valid_email(email) or email in existing:
            skipped += 1
            continue
        existing.add(email)
        db.add(
            HotlistRecipient(
                hotlist_id=hotlist.id,
                kind=kind,
                first_name=record.get("first_name"),
                last_name=record.get("last_name"),
                email=email,
                company=record.get("company"),
                client_id=record.get("client_id"),
                vendor_id=record.get("vendor_id"),
            )
        )
        added += 1
    db.commit()
    db.refresh(hotlist)
    return added, skipped


def add_manual_recipients(db: Session, hotlist: Hotlist, records: list[dict]) -> tuple[int, int]:
    return _add_recipients(db, hotlist, records, HotlistRecipientKind.MANUAL.value)


def import_recipients_from_workbook(db: Session, hotlist: Hotlist, data: bytes) -> dict:
    """Bulk-load recipients from an uploaded spreadsheet."""
    records, problems = parse_recipient_workbook(data)
    if not records and problems:
        raise ValidationAppError(problems[0])

    added, skipped = _add_recipients(db, hotlist, records, HotlistRecipientKind.IMPORTED.value)
    return {
        "parsed": len(records),
        "added": added,
        "skipped": skipped,
        "problems": problems,
    }


def add_client_recipients(db: Session, hotlist: Hotlist, client_ids: list[uuid.UUID]) -> tuple[int, int]:
    """Pull every known contact address for the given clients."""
    records: list[dict] = []
    clients = list(
        db.scalars(select(Client).where(Client.id.in_(client_ids), Client.organization_id == hotlist.organization_id)).all()
    )
    for client in clients:
        if client.email_id:
            records.append({"email": client.email_id, "company": client.name, "client_id": client.id})

        for contact in db.scalars(select(ClientContact).where(ClientContact.client_id == client.id)).all():
            if contact.email:
                first, _, last = (contact.name or "").partition(" ")
                records.append(
                    {
                        "first_name": first or None,
                        "last_name": last or None,
                        "email": contact.email,
                        "company": client.name,
                        "client_id": client.id,
                    }
                )

        for account in db.scalars(select(ClientAccount).where(ClientAccount.client_id == client.id)).all():
            if account.email_id:
                first, _, last = (account.contact_person or "").partition(" ")
                records.append(
                    {
                        "first_name": first or None,
                        "last_name": last or None,
                        "email": account.email_id,
                        "company": client.name,
                        "client_id": client.id,
                    }
                )

    return _add_recipients(db, hotlist, records, HotlistRecipientKind.CLIENT.value)


def add_vendor_recipients(db: Session, hotlist: Hotlist, vendor_ids: list[uuid.UUID]) -> tuple[int, int]:
    records: list[dict] = []
    vendors = list(
        db.scalars(select(Vendor).where(Vendor.id.in_(vendor_ids), Vendor.organization_id == hotlist.organization_id)).all()
    )
    for vendor in vendors:
        if vendor.email_id:
            records.append({"email": vendor.email_id, "company": vendor.name, "vendor_id": vendor.id})
    return _add_recipients(db, hotlist, records, HotlistRecipientKind.VENDOR.value)


def remove_recipient(db: Session, hotlist: Hotlist, recipient_id: uuid.UUID) -> None:
    row = db.scalar(
        select(HotlistRecipient).where(HotlistRecipient.id == recipient_id, HotlistRecipient.hotlist_id == hotlist.id)
    )
    if row is None:
        raise NotFoundError("Recipient not found")
    db.delete(row)
    db.commit()


def set_recipient_unsubscribed(
    db: Session, hotlist: Hotlist, recipient_id: uuid.UUID, unsubscribed: bool
) -> HotlistRecipient:
    row = db.scalar(
        select(HotlistRecipient).where(HotlistRecipient.id == recipient_id, HotlistRecipient.hotlist_id == hotlist.id)
    )
    if row is None:
        raise NotFoundError("Recipient not found")
    row.unsubscribed = unsubscribed
    db.commit()
    db.refresh(row)
    return row


# ----------------------------------------------------------------------- sends


def sendable_recipients(hotlist: Hotlist) -> list[HotlistRecipient]:
    return [r for r in hotlist.recipients if not r.unsubscribed]


def create_send(db: Session, hotlist: Hotlist, *, actor_id: uuid.UUID | None) -> HotlistSend:
    """Record the intent to send, and validate that it can go out."""
    if not hotlist.members:
        raise ValidationAppError("Add at least one consultant before sending this hotlist.")

    recipients = sendable_recipients(hotlist)
    if not recipients:
        raise ValidationAppError("Add at least one recipient who has not unsubscribed.")
    if not (hotlist.subject or "").strip():
        raise ValidationAppError("The hotlist needs an email subject.")

    send = HotlistSend(
        hotlist_id=hotlist.id,
        status=HotlistSendStatus.PENDING.value,
        subject=hotlist.subject,
        member_count=len(hotlist.members),
        recipient_count=len(recipients),
        sent_by=actor_id,
    )
    db.add(send)
    db.commit()
    db.refresh(send)
    return send


def record_delivery(db: Session, send: HotlistSend, *, email: str, delivered: bool, error: str | None = None) -> None:
    db.add(
        HotlistDelivery(
            hotlist_send_id=send.id,
            recipient_email=email,
            status=OutboundMessageStatus.SENT.value if delivered else OutboundMessageStatus.FAILED.value,
            error_message=error,
        )
    )
    if delivered:
        send.sent_count += 1
    else:
        send.failed_count += 1
    db.commit()


def finish_send(db: Session, send: HotlistSend, *, error: str | None = None) -> None:
    send.completed_at = datetime.now(UTC)
    # "Completed" as long as something got through; a wholly failed batch is a
    # failure worth surfacing.
    if error is not None:
        send.status = HotlistSendStatus.FAILED.value
        send.error_message = error
    elif send.sent_count == 0:
        send.status = HotlistSendStatus.FAILED.value
        send.error_message = "No recipient accepted the message."
    else:
        send.status = HotlistSendStatus.COMPLETED.value

    hotlist = db.get(Hotlist, send.hotlist_id)
    if hotlist is not None and send.sent_count:
        hotlist.status = HotlistStatus.SENT.value
    db.commit()


def list_sends(db: Session, hotlist: Hotlist) -> list[HotlistSend]:
    return list(
        db.scalars(
            select(HotlistSend).where(HotlistSend.hotlist_id == hotlist.id).order_by(HotlistSend.created_at.desc())
        ).all()
    )


def suggest_members(
    db: Session, organization_id: uuid.UUID, *, viewer: CurrentUser | None = None, limit: int = 25
) -> list[BenchProfile]:
    """Active bench consultants, longest-benched first.

    Whoever has been sitting longest is who most needs marketing, so that is
    the default ordering when building a new hotlist.
    """
    profiles = bench_service.list_profiles(db, organization_id, viewer=viewer, status="Active Bench")
    return sorted(profiles, key=lambda p: p.bench_age_days, reverse=True)[:limit]
