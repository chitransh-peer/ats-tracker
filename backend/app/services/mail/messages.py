"""Bodies for the transactional email the platform sends.

Kept separate from the SMTP transport so wording can change without touching
delivery, and so tests can assert on content without a mail server. Every
function returns ``(subject, text_body, html_body)`` — the plain-text part is
always populated, because it is what spam filters read and some clients prefer.
"""

from datetime import datetime
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


def invitation(
    *,
    full_name: str,
    email: str,
    temporary_password: str,
    organization_name: str,
    role_name: str,
    expires_at: datetime | None,
) -> tuple[str, str, str]:
    """The one email that carries a credential.

    The temporary password is shown in full because the recipient has to type
    it, and it is the only copy -- nothing can recover it afterwards. Both the
    address to sign in with and the deadline are spelled out, since the account
    is useless without the first and dead after the second.
    """
    base = get_settings().app_base_url.rstrip("/")
    url = f"{base}/auth/login"
    role_label = role_name.replace("_", " ")
    subject = f"Your {organization_name} account is ready"
    deadline = expires_at.strftime("%d %b %Y at %H:%M UTC") if expires_at is not None else None
    expiry_sentence = (
        f"This temporary password stops working on {deadline}."
        if deadline
        else "This temporary password works until you sign in and change it."
    )

    text = (
        f"Hello {full_name},\n\n"
        f"An account has been created for you at {organization_name} on ATS Tracker "
        f"as a {role_label}.\n\n"
        f"Sign in at: {url}\n"
        f"Email: {email}\n"
        f"Temporary password: {temporary_password}\n\n"
        f"{expiry_sentence} You will be asked to choose your own password as soon "
        "as you sign in, and this one stops working at that point.\n\n"
        "If you were not expecting this, you can ignore this email -- the account "
        "cannot be used until someone signs in with the password above.\n"
    )

    html = layout.render(
        heading="Your account is ready",
        preheader=f"Sign in to {organization_name} with your temporary password.",
        body_html=(
            layout.paragraph(f"Hello {escape(full_name)},")
            + layout.paragraph(
                f"An account has been created for you at {escape(organization_name)} "
                f"on ATS Tracker as a {escape(role_label)}."
            )
            + layout.paragraph("Sign in with this email address and temporary password:")
            + layout.code_block(escape(email))
            + layout.code_block(escape(temporary_password))
            + layout.button(url, "Sign in")
            + layout.muted(
                f"{escape(expiry_sentence)} You will be asked to choose your own password "
                "as soon as you sign in, and this one stops working at that point."
            )
            + layout.muted(
                "If you were not expecting this, you can ignore this email - the account "
                "cannot be used until someone signs in with the password above."
            )
        ),
        footer_note=f"Sent by {organization_name} because an account was created for you.",
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
