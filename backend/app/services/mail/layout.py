"""Shared HTML shell for transactional email.

Every message the platform sends goes through :func:`render`, so password
resets, invitations and hotlists all arrive looking like they came from the same
company rather than three different scripts.

Constraints that shape the markup:

* **Tables, not flexbox.** Outlook renders through Word's engine and ignores
  modern layout.
* **Inline styles only.** Gmail strips `<style>` blocks in many contexts.
* **No external images.** Remote assets are blocked by default in most clients,
  so the wordmark is text. Nothing here depends on a network fetch.
* **A plain-text alternative is always sent alongside** (see `messages.py`) —
  it is what spam filters read, and some recipients prefer it.
"""

from html import escape

from app.core.config import get_settings

# Kept in step with the application's own palette.
_INK = "#12211f"
_MUTED = "#6e7a78"
_ACCENT = "#0f5f5c"
_BORDER = "#dedbd2"
_CANVAS = "#f4f3ee"
_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"


def button(url: str, label: str) -> str:
    """A call-to-action rendered as a table so Outlook honours the padding."""
    return f"""
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0;">
        <tr>
          <td align="center" bgcolor="{_ACCENT}" style="border-radius:6px;">
            <a href="{escape(url, quote=True)}"
               style="display:inline-block;padding:13px 30px;font-family:{_FONT};
                      font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;">
              {escape(label)}
            </a>
          </td>
        </tr>
      </table>"""


def render(*, heading: str, body_html: str, preheader: str | None = None, footer_note: str | None = None) -> str:
    """Wrap message content in the branded shell.

    ``body_html`` is inserted as-is, so callers are responsible for escaping any
    user-supplied values they interpolate into it.
    """
    settings = get_settings()
    org = escape(settings.default_org_name)
    year_note = escape(footer_note) if footer_note else ""

    # Hidden preview line: what inboxes show next to the subject.
    preheader_block = (
        f'<div style="display:none;font-size:1px;color:{_CANVAS};max-height:0;overflow:hidden;">{escape(preheader)}</div>'
        if preheader
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(heading)}</title>
</head>
<body style="margin:0;padding:0;background-color:{_CANVAS};">
{preheader_block}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:{_CANVAS};padding:32px 12px;">
  <tr>
    <td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="max-width:560px;background-color:#ffffff;border:1px solid {_BORDER};border-radius:8px;">

        <tr>
          <td style="padding:26px 32px 0 32px;">
            <div style="font-family:{_FONT};font-size:15px;font-weight:700;color:{_ACCENT};
                        letter-spacing:-0.01em;">{org}</div>
            <div style="font-family:{_FONT};font-size:10px;font-weight:600;color:{_MUTED};
                        letter-spacing:0.12em;text-transform:uppercase;margin-top:2px;">
              Recruiting
            </div>
          </td>
        </tr>

        <tr><td style="padding:20px 32px 0 32px;">
          <div style="height:1px;background-color:{_BORDER};line-height:1px;">&nbsp;</div>
        </td></tr>

        <tr>
          <td style="padding:24px 32px 8px 32px;">
            <h1 style="margin:0;font-family:{_FONT};font-size:21px;line-height:1.3;
                       font-weight:700;color:{_INK};letter-spacing:-0.02em;">{escape(heading)}</h1>
          </td>
        </tr>

        <tr>
          <td style="padding:0 32px 8px 32px;font-family:{_FONT};font-size:15px;
                     line-height:1.62;color:{_INK};">
            {body_html}
          </td>
        </tr>

        <tr><td style="padding:12px 32px 0 32px;">
          <div style="height:1px;background-color:{_BORDER};line-height:1px;">&nbsp;</div>
        </td></tr>

        <tr>
          <td style="padding:16px 32px 28px 32px;font-family:{_FONT};font-size:12px;
                     line-height:1.6;color:{_MUTED};">
            {year_note or f"Sent by {org} recruiting."}
          </td>
        </tr>
      </table>

      <div style="font-family:{_FONT};font-size:11px;color:{_MUTED};margin-top:16px;">
        This is an automated message — please do not reply to it.
      </div>
    </td>
  </tr>
</table>
</body>
</html>"""


def paragraph(text: str) -> str:
    """An escaped paragraph, for plain sentences of message copy."""
    return f'<p style="margin:0 0 14px 0;">{escape(text)}</p>'


def muted(text: str) -> str:
    return f'<p style="margin:0 0 14px 0;font-size:13px;color:{_MUTED};">{escape(text)}</p>'


def code_block(value: str) -> str:
    """For a URL or token the recipient may need to copy by hand."""
    return (
        f'<p style="margin:0 0 14px 0;font-size:12px;color:{_MUTED};word-break:break-all;'
        f"background-color:{_CANVAS};border:1px solid {_BORDER};border-radius:4px;padding:10px 12px;"
        f'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;">{escape(value)}</p>'
    )
