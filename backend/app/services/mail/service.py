"""Outbound email delivery over SMTP.

Sending is optional: when ``smtp_host`` is unset the transport is disabled and
``send_email`` reports failure without raising, so callers can log the message
and continue. That keeps local development and the recruiter pilot working
before real SMTP credentials exist.
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MailNotConfiguredError(RuntimeError):
    """Raised only by callers that treat an undeliverable message as an error."""


def _build_message(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = formataddr((settings.mail_from_name, settings.mail_from_email))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    for file_name, data, mime_type in attachments or []:
        maintype, _, subtype = mime_type.partition("/")
        message.add_attachment(
            data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=file_name
        )
    return message


def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    """Deliver one message. Returns True only if SMTP accepted it.

    Never raises: email is a side effect of the request that triggered it, and a
    dead mail server must not fail the underlying operation (a password reset is
    still recorded, an invitation is still valid).
    """
    settings = get_settings()

    if not settings.mail_enabled:
        logger.warning("Email not sent (no SMTP host configured): to=%s subject=%s", to, subject)
        return False

    message = _build_message(to=to, subject=subject, text_body=text_body, html_body=html_body, attachments=attachments)

    try:
        if settings.smtp_use_ssl:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
            )
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds)

        with smtp:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                smtp.starttls()
            # Some providers (e.g. a local relay) accept unauthenticated submission.
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception:
        logger.exception("SMTP delivery failed: to=%s subject=%s", to, subject)
        return False

    logger.info("Email sent: to=%s subject=%s", to, subject)
    return True
