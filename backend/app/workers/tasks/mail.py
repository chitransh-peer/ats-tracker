import uuid

import dramatiq

from app.core.enums import OutboundMessageStatus
from app.db.models.candidate import Candidate
from app.db.models.communication import OutboundMessage
from app.db.session import SessionLocal
from app.services.mail.service import send_email
from app.workers.broker import broker  # noqa: F401  (ensures the broker is configured)


@dramatiq.actor(max_retries=3)
def send_email_task(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """Fire-and-forget delivery for transactional mail (resets, invitations)."""
    send_email(to=to, subject=subject, text_body=text_body, html_body=html_body)


@dramatiq.actor(max_retries=3)
def send_outbound_message_task(message_id: str) -> None:
    """Deliver a logged candidate message and record whether it actually went out."""
    db = SessionLocal()
    try:
        message = db.get(OutboundMessage, uuid.UUID(message_id))
        if message is None:
            return

        candidate = db.get(Candidate, message.candidate_id) if message.candidate_id is not None else None
        recipient = candidate.email if candidate else None
        if not recipient:
            message.status = OutboundMessageStatus.FAILED.value
            db.commit()
            return

        delivered = send_email(
            to=recipient,
            subject=message.subject,
            text_body=message.body,
        )
        message.status = OutboundMessageStatus.SENT.value if delivered else OutboundMessageStatus.FAILED.value
        db.commit()
    finally:
        db.close()


@dramatiq.actor(max_retries=0, time_limit=600_000)
def send_hotlist_task(send_id: str) -> None:
    """Deliver one hotlist to every subscribed recipient.

    max_retries=0 on purpose: a retry would re-send to recipients who already
    received it, and duplicate hotlists damage a vendor relationship far more
    than one missed send. Per-recipient outcomes are recorded instead, so a
    failure can be retried deliberately from the UI.
    """
    from app.core.enums import HotlistSendStatus
    from app.db.models.hotlist import HotlistSend
    from app.db.models.user import User
    from app.services.hotlist import service as hotlist_service
    from app.services.hotlist.spreadsheet import build_hotlist_workbook
    from app.services.mail import messages as mail_messages

    db = SessionLocal()
    try:
        send = db.get(HotlistSend, uuid.UUID(send_id))
        if send is None:
            return

        hotlist = send.hotlist
        send.status = HotlistSendStatus.SENDING.value
        db.commit()

        sender = db.get(User, send.sent_by) if send.sent_by else None
        sender_name = sender.full_name if sender else None
        recipients = hotlist_service.sendable_recipients(hotlist)

        attachments: list[tuple[str, bytes, str]] = []
        if hotlist.attach_spreadsheet:
            try:
                workbook = build_hotlist_workbook(
                    hotlist_name=hotlist.name,
                    profiles=list(hotlist.members),
                    include_rates=hotlist.include_rates,
                    include_candidate_contact=hotlist.include_candidate_contact,
                )
                safe_name = "".join(c if c.isalnum() or c in "-_ " else "-" for c in hotlist.name).strip()
                attachments.append(
                    (
                        f"{safe_name or 'hotlist'}.xlsx",
                        workbook,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - surfaced on the send record
                hotlist_service.finish_send(db, send, error=f"Could not build the spreadsheet: {exc}")
                return

        for recipient in recipients:
            text_body, html_body = mail_messages.hotlist(
                subject=send.subject,
                body=hotlist.body or "",
                recipient_first_name=recipient.first_name,
                sender_name=sender_name,
                consultant_count=send.member_count,
                has_attachment=bool(attachments),
            )
            delivered = send_email(
                to=recipient.email,
                subject=send.subject,
                text_body=text_body,
                html_body=html_body,
                attachments=attachments,
            )
            hotlist_service.record_delivery(
                db,
                send,
                email=recipient.email,
                delivered=delivered,
                error=None if delivered else "SMTP delivery failed",
            )

        hotlist_service.finish_send(db, send)
    finally:
        db.close()
