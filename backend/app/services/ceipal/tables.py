"""The tables of a Ceipal "applicants" backup, and how they fit together.

Ceipal names the files after the table (Applicants.csv, Applicant_Documents.csv
...) and writes them MySQL-style: quotes escaped with a backslash, NULL as
`\\N`. The browser parses them (frontend/lib/ceipal/csv.ts) and sends rows as
{header: value}; everything below works from those.

Every child table links to an applicant by `Applicants.Id` -- not by the
"Applicant Id" column, which is a different number. A documents row for
Forrest Hardin carries 114453, his Id; his Applicant Id is 114600.
Header spelling varies between tables ("Applicant ID" / "Applicant Id"), so
headers are looked up case-insensitively.
"""

from dataclasses import dataclass

NULL_MARKER = "\\N"


@dataclass(frozen=True)
class Table:
    kind: str
    file_stem: str
    # Header holding the Applicants.Id this row belongs to.
    ref_header: str | None
    # Header holding what else the row is looked up by.
    key_header: str | None
    required: tuple[str, ...]


TABLES: tuple[Table, ...] = (
    Table("applicants", "applicants", "Id", "Applicant Id", ("Id",)),
    Table(
        "documents",
        "applicant_documents",
        "Applicant ID",
        "Converted Document Name",
        ("Applicant ID", "Converted Document Name"),
    ),
    Table("education", "applicant_education_details", "Applicant Id", None, ("Applicant Id",)),
    Table("notes", "applicant_action_notes", "Applicant ID", None, ("Applicant ID",)),
    Table("submissions", "submissions", "Applicant Id", "Submission Id", ("Applicant Id",)),
    Table("submission_notes", "submission_notes", None, "Submission Id", ("Submission Id",)),
    Table("users", "user_profiles", None, "Id", ("Id", "Email")),
    Table("degrees", "master_data_degrees", None, "Id", ("Id", "Name")),
)
TABLES_BY_KIND = {t.kind: t for t in TABLES}
TABLES_BY_STEM = {t.file_stem: t for t in TABLES}

# Never stored, not even while staged.
DROPPED_HEADERS = {"ssn", "date of birth"}

# The Applicants columns, in Ceipal's order, less the dropped ones. This is
# the Ceipal view of the candidate list. A column a later export adds still
# shows -- it is appended after these -- so the view never loses data.
APPLICANT_COLUMNS: tuple[str, ...] = (
    "Id",
    "Record Type",
    "Applicant Id",
    "Bench Id",
    "First Name",
    "Last Name",
    "Middle Name",
    "Nick Name",
    "Mobile",
    "Home Phone Number",
    "Work Phone Number",
    "Other Phone",
    "Work Authorization",
    "Skype Id",
    "Source",
    "City",
    "Address",
    "State",
    "Country",
    "Postal Code",
    "Linkedin Url",
    "Facebook Url",
    "Twitter Url",
    "Current Company",
    "Email",
    "Alternate Email Address",
    "Expected Pay",
    "Video Reference",
    "JOb Title",
    "Experience",
    "Gender",
    "Preferred Location",
    "Status",
    "Expected Salary",
    "Primary Skills",
    "Skills",
    "Created By",
    "Referred By",
    "Owners",
    "Created At",
    "Modified At",
)

# Columns holding Ceipal user ids, shown as the user's email instead.
USER_COLUMNS = ("Created By", "Owners")


def table_for_file(file_name: str) -> Table | None:
    """Applicants.csv, path/to/APPLICANTS.CSV and Applicants (1).csv all name
    the applicants table."""
    base = file_name.replace("\\", "/").rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0].strip().lower()
    stem = stem.split(" (", 1)[0].strip()
    return TABLES_BY_STEM.get(stem)


def clean_row(row: dict) -> dict[str, str]:
    """Strings only, trimmed, NULL markers emptied, dropped columns gone."""
    cleaned: dict[str, str] = {}
    for header, value in row.items():
        name = str(header).strip()
        if not name or name.lower() in DROPPED_HEADERS:
            continue
        text = "" if value is None else str(value).strip()
        cleaned[name] = "" if text == NULL_MARKER else text
    return cleaned


def get(row: dict, header: str) -> str:
    """A value by header, ignoring how Ceipal capitalised it in this table."""
    if header in row:
        return row[header] or ""
    wanted = header.lower()
    for name, value in row.items():
        if name.lower() == wanted:
            return value or ""
    return ""


def has_header(headers: list[str], header: str) -> bool:
    wanted = header.lower()
    return any(h.strip().lower() == wanted for h in headers)
