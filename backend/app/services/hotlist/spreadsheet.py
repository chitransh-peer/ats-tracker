"""Excel generation and parsing for hotlists.

Two independent sheets, matching the two ways a hotlist uses a spreadsheet:

  * :func:`build_hotlist_workbook` — the consultant list that goes out as an
    email attachment.
  * :func:`parse_recipient_workbook` — a bulk upload of who should receive it.

Both keep ``First Name`` / ``Last Name`` / ``Email`` as the leading columns, so
the exported file can be fed straight back in as a recipient list.
"""

import io
import re
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Deliberately permissive: the aim is to reject obvious junk from a spreadsheet
# cell, not to adjudicate the RFC. Real validation is the mail server bouncing.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")

_HEADER_FILL = PatternFill("solid", fgColor="0F5F5C")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)


def split_name(full_name: str) -> tuple[str, str]:
    """Split a stored full name into first and last.

    Candidates are stored with a single ``full_name``, but hotlists are
    conventionally first/last. Everything after the first token becomes the
    surname, which handles multi-word family names better than taking only the
    final token.
    """
    parts = (full_name or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def is_valid_email(value: str | None) -> bool:
    return bool(value) and bool(_EMAIL_RE.match(value.strip()))


def _write_header(ws, headers: list[str]) -> None:
    ws.append(headers)
    for idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"


def _autosize(ws, headers: list[str], rows: list[list[Any]]) -> None:
    for idx, header in enumerate(headers, start=1):
        widest = max(
            [len(str(header))] + [len(str(r[idx - 1])) for r in rows if r[idx - 1] is not None],
            default=10,
        )
        ws.column_dimensions[get_column_letter(idx)].width = min(max(widest + 2, 12), 48)


def build_hotlist_workbook(
    *,
    hotlist_name: str,
    profiles: list[Any],
    include_rates: bool = True,
    include_candidate_contact: bool = False,
) -> bytes:
    """Render the consultant list as .xlsx bytes.

    ``include_candidate_contact`` is off by default. Sending consultant phone
    numbers and email addresses to a vendor list is how a bench gets poached,
    so it has to be an explicit choice per hotlist.
    """
    headers = ["First Name", "Last Name", "Email"] if include_candidate_contact else ["First Name", "Last Name"]
    headers += ["Job Title", "Experience (yrs)", "Skills", "Work Authorization", "Location", "Available From"]
    if include_rates:
        headers += ["Desired Rate", "Tax Term"]
    headers += ["Bench ID"]

    rows: list[list[Any]] = []
    for member in profiles:
        profile = getattr(member, "bench_profile", member)
        candidate = profile.candidate
        first, last = split_name(candidate.full_name)

        row: list[Any] = [first, last]
        if include_candidate_contact:
            row.append(candidate.email)
        row += [
            getattr(member, "headline_override", None) or profile.marketing_title or candidate.current_title or "",
            float(candidate.total_experience_years) if candidate.total_experience_years is not None else None,
            ", ".join(candidate.skills or []),
            candidate.work_auth or "",
            profile.preferred_locations or candidate.location or "",
            profile.available_from.isoformat() if profile.available_from else "Immediate",
        ]
        if include_rates:
            rate = (
                f"{profile.rate_currency} {profile.desired_rate:.2f} / {profile.rate_unit}"
                if profile.desired_rate is not None
                else ""
            )
            row += [rate, profile.tax_term or ""]
        row.append(profile.bench_code)
        rows.append(row)

    wb = Workbook()
    ws = wb.active
    # Excel rejects sheet titles over 31 chars or containing []:*?/\
    ws.title = re.sub(r"[\[\]:*?/\\]", "-", hotlist_name)[:31] or "Hotlist"

    _write_header(ws, headers)
    for row in rows:
        ws.append(row)
    _autosize(ws, headers, rows)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_recipient_template_workbook() -> bytes:
    """A blank recipient sheet for people to fill in and upload back."""
    headers = ["First Name", "Last Name", "Email", "Company"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Recipients"
    _write_header(ws, headers)
    example = ["Jane", "Doe", "jane.doe@example.com", "Example Staffing LLC"]
    ws.append(example)
    _autosize(ws, headers, [example])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def parse_recipient_workbook(data: bytes) -> tuple[list[dict], list[str]]:
    """Read a recipient spreadsheet.

    Returns ``(recipients, problems)``. Header matching is case- and
    space-insensitive, and a few common aliases are accepted, because these
    files are usually maintained by hand and rarely match a fixed format.

    Bad rows are reported rather than aborting the whole import: one typo in
    row 40 should not discard the other 39.
    """
    aliases = {
        "first name": "first_name",
        "firstname": "first_name",
        "fname": "first_name",
        "last name": "last_name",
        "lastname": "last_name",
        "lname": "last_name",
        "surname": "last_name",
        "email": "email",
        "email address": "email",
        "email id": "email",
        "mail id": "email",
        "e-mail": "email",
        "company": "company",
        "company name": "company",
        "vendor": "company",
        "client": "company",
        "organisation": "company",
        "organization": "company",
    }

    problems: list[str] = []
    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        return [], [f"Could not read the file as an Excel workbook: {exc}"]

    ws = wb.active
    rows = ws.iter_rows(values_only=True)

    try:
        header_row = next(rows)
    except StopIteration:
        return [], ["The sheet is empty."]

    columns: dict[int, str] = {}
    for idx, raw in enumerate(header_row):
        if raw is None:
            continue
        key = aliases.get(str(raw).strip().lower())
        if key:
            columns[idx] = key

    if "email" not in columns.values():
        return [], [
            "No email column found. The sheet needs a header row with at least "
            "'Email' (plus optionally 'First Name', 'Last Name', 'Company')."
        ]

    recipients: list[dict] = []
    seen: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue

        record = {"first_name": None, "last_name": None, "email": None, "company": None}
        for idx, field in columns.items():
            if idx < len(row) and row[idx] is not None:
                record[field] = str(row[idx]).strip() or None

        email = (record["email"] or "").lower()
        if not email:
            problems.append(f"Row {row_number}: no email address — skipped.")
            continue
        if not is_valid_email(email):
            problems.append(f"Row {row_number}: '{record['email']}' is not a valid email — skipped.")
            continue
        if email in seen:
            problems.append(f"Row {row_number}: duplicate of {email} — skipped.")
            continue

        seen.add(email)
        record["email"] = email
        recipients.append(record)

    return recipients, problems
