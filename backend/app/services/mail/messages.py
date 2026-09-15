"""Bodies for the transactional email the platform sends.

Kept separate from the SMTP transport so wording can change without touching
delivery, and so tests can assert on content without a mail server. Every
function returns ``(subject, text_body, html_body)`` — the plain-text part is
always populated, because it is what spam filters read and some clients prefer.
"""

from html import escape
from urllib.parse import quote

from app.core.config import get_settings
from app.services.mail import layout


def _link(path: str, token: str) -> str:
    base = get_settings().app_base_url.rstrip("/")
    # safe="" so a token containing "/" cannot alter the URL path.
    return f"{base}{path}?token={quote(token, safe='')}"


def _org_name() -> str:
    return get_settings().default_org_name


def password_reset(*, token: str, expires_in_minutes: int) -> tuple[str, str, str]:
    url = _link("/auth/reset-password", token)
    org = _org_name()
    subject = f"Reset your {org} password"

    text = (
        f"We received a request to reset your {org} recruiting password.\n\n"
        f"Open this link to choose a new one:\n{url}\n\n"
        f"The link expires in {expires_in_minutes} minutes and can be used once.\n\n"
        "If you didn't ask for a reset you can ignore this email — your password "
        "stays as it is, and nobody has been given access to your account.\n"
    )

    html = layout.render(
        heading="Reset your password",
        preheader=f"Your reset link expires in {expires_in_minutes} minutes.",
        body_html=(
            layout.paragraph(f"We received a request to reset the password for your {org} recruiting account.")
            + layout.button(url, "Choose a new password")
            + layout.muted(f"This link expires in {expires_in_minutes} minutes and can only be used once.")
            + layout.paragraph(
                "If you didn't ask for a reset, you can ignore this email. Your password "
                "stays as it is and nobody has been given access to your account."
            )
            + layout.muted("If the button doesn't work, copy this address into your browser:")
            + layout.code_block(url)
        ),
        footer_note=f"Sent by {org} because a password reset was requested for this address.",
    )
    return subject, text, html


def invitation(*, token: str, organization_name: str, role_name: str) -> tuple[str, str, str]:
    url = _link("/auth/invite/accept", token)
    role_label = role_name.replace("_", " ")
    subject = f"You've been invited to {organization_name} on ATS Tracker"

    text = (
        f"You've been invited to join {organization_name} on ATS Tracker as a {role_label}.\n\n"
        f"Set your name and password to activate your account:\n{url}\n\n"
        "Your password is chosen by you and is never visible to anyone else, "
        "including the person who invited you.\n"
    )

    html = layout.render(
        heading="You've been invited",
        preheader=f"Activate your {organization_name} recruiting account.",
        body_html=(
            layout.paragraph(f"You've been invited to join {organization_name} on ATS Tracker as a {role_label}.")
            + layout.paragraph("Set your name and a password to activate your account.")
            + layout.button(url, "Activate your account")
            + layout.muted(
                "You choose your own password — it is never visible to anyone else, including the person who invited you."
            )
            + layout.muted("If the button doesn't work, copy this address into your browser:")
            + layout.code_block(url)
        ),
        footer_note=f"Sent by {organization_name} because you were invited to their recruiting workspace.",
    )
    return subject, text, html


def account_created(*, full_name: str, email: str, role_names: list[str]) -> tuple[str, str, str]:
    """Confirmation once an invited user has activated their account.

    Sent after the fact rather than containing any credential, so it is safe if
    it sits in an inbox: it tells someone their account is live and, crucially,
    gives them a way to react if it wasn't them.
    """
    settings = get_settings()
    org = settings.default_org_name
    sign_in = f"{settings.app_base_url.rstrip('/')}/auth/login"
    roles = ", ".join(r.replace("_", " ") for r in role_names) or "user"
    first_name = (full_name or "").split(" ")[0] or "there"
    subject = f"Your {org} account is ready"

    text = (
        f"Hello {first_name},\n\n"
        f"Your {org} recruiting account has been created.\n\n"
        f"  Email: {email}\n"
        f"  Access level: {roles}\n\n"
        f"Sign in here: {sign_in}\n\n"
        "If you did not set up this account, contact your administrator immediately — "
        "someone may have used your email address by mistake.\n"
    )

    html = layout.render(
        heading="Your account is ready",
        preheader=f"You can now sign in to {org} recruiting.",
        body_html=(
            layout.paragraph(f"Hello {first_name},")
            + layout.paragraph(f"Your {org} recruiting account has been created and is ready to use.")
            + f"""
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                   style="margin:0 0 16px 0;border:1px solid #dedbd2;border-radius:6px;">
              <tr>
                <td style="padding:12px 14px;font-size:13px;color:#6e7a78;width:38%;">Email</td>
                <td style="padding:12px 14px;font-size:13px;color:#12211f;font-weight:600;">{escape(email)}</td>
              </tr>
              <tr>
                <td style="padding:0 14px 12px 14px;font-size:13px;color:#6e7a78;">Access level</td>
                <td style="padding:0 14px 12px 14px;font-size:13px;color:#12211f;font-weight:600;
                           text-transform:capitalize;">{escape(roles)}</td>
              </tr>
            </table>"""
            + layout.button(sign_in, "Sign in")
            + layout.paragraph(
                "If you did not set up this account, contact your administrator immediately — "
                "someone may have used your email address by mistake."
            )
        ),
        footer_note=f"Sent by {org} because an account was activated for this address.",
    )
    return subject, text, html


def hotlist(
    *,
    subject: str,
    body: str,
    recipient_first_name: str | None,
    sender_name: str | None,
    consultant_count: int,
    has_attachment: bool,
) -> tuple[str, str]:
    """Render a recruiter-written hotlist email.

    Returns ``(text_body, html_body)`` — the subject is supplied by the sender.
    ``body`` is recruiter-authored plain text: it is escaped and newlines become
    paragraphs, so no HTML from the composer can reach the recipient.
    """
    greeting = f"Hi {recipient_first_name}," if recipient_first_name else "Hello,"
    signoff = f"Best regards,\n{sender_name}" if sender_name else "Best regards,"

    attachment_note = (
        f"The attached spreadsheet has the full details for all {consultant_count} "
        f"consultant{'s' if consultant_count != 1 else ''}."
        if has_attachment
        else ""
    )

    text_parts = [greeting, "", body.strip()]
    if attachment_note:
        text_parts += ["", attachment_note]
    text_parts += ["", signoff, ""]
    text = "\n".join(text_parts)

    paragraphs = "".join(layout.paragraph(chunk.strip()) for chunk in body.split("\n\n") if chunk.strip())

    html = layout.render(
        heading=subject,
        preheader=f"{consultant_count} available consultant{'s' if consultant_count != 1 else ''}.",
        body_html=(
            layout.paragraph(greeting)
            + paragraphs
            + (layout.muted(attachment_note) if attachment_note else "")
            + layout.paragraph(signoff.replace("\n", " — "))
        ),
        footer_note=(
            f"Sent by {_org_name()} recruiting. Reply to this address to be removed "
            "from future consultant availability lists."
        ),
    )
    return text, html
