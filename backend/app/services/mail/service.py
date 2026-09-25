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


def send_email_reporting_errors(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> str | None:
    """Send one message and return why it failed, or None if it went out.

    send_email deliberately never raises and never says why -- a dead mail
    server must not fail the password reset that triggered it. That is right
    for the app and useless for an operator, who is left with a silent failure
    and no way to see the reason without host log access.

    This is the same send with the reason kept, for the test endpoint only.
    """
    settings = get_settings()
    if not settings.mail_enabled:
        return "No SMTP host is configured (SMTP_HOST is empty)."

    message = _build_message(to=to, subject=subject, text_body=text_body, html_body=html_body)

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
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        logger.warning("SMTP authentication rejected for %s", settings.smtp_username)
        # The provider's own words are the useful part: "account not activated"
        # and "bad credentials" look identical from outside and are fixed very
        # differently.
        return f"The mail server rejected these credentials: {exc.smtp_error.decode(errors='replace')}"
    except smtplib.SMTPRecipientsRefused:
        return f"The mail server refused the recipient address {to}."
    except smtplib.SMTPSenderRefused as exc:
        return (
            f"The mail server refused to send as {settings.mail_from_email}. "
            "Check the sender is verified with your provider. "
            f"Server said: {exc.smtp_error.decode(errors='replace')}"
        )
    except OSError as exc:
        # Covers DNS failure, refused connection and timeout alike.
        return f"Could not reach {settings.smtp_host}:{settings.smtp_port} — {exc}"
    except Exception as exc:  # noqa: BLE001 - reported to the operator verbatim
        logger.exception("Unexpected SMTP failure")
        return f"Unexpected failure: {type(exc).__name__}: {exc}"

    logger.info("Test email sent: to=%s", to)
    return None


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
