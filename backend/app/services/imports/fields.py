"""What an importable field is, and how a raw text value becomes one.

`convert` returns the typed value, or raises FieldError with a message written
for the person fixing the spreadsheet ("Openings must be a whole number, got
'three'"), because that message is what the rejected-rows report shows them.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

# Values that mean "nothing here" in exported spreadsheets.
_EMPTY_MARKERS = {"", "-", "--", "n/a", "na", "null", "none", "nil", "not available", "#n/a"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TRUE = {"yes", "y", "true", "t", "1", "on"}
_FALSE = {"no", "n", "false", "f", "0", "off"}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
)
_DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y %I:%M:%S %p",
)


class FieldError(ValueError):
    pass


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"  # text | email | phone | int | decimal | bool | date | datetime | list | choice | note
    required: bool = False
    max_length: int | None = None
    # Other header names this field is commonly exported under, for guessing
    # the mapping. Compared after lower-casing and dropping punctuation.
    aliases: tuple[str, ...] = ()
    # For "choice": the allowed values; anything else falls back to `default`
    # with a warning rather than losing the row.
    choices: tuple[str, ...] = ()
    default: str | None = None
    help: str | None = None
    names: tuple[str, ...] = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "names", tuple({normalize_header(n) for n in (self.key, self.label, *self.aliases)}))


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def is_empty(raw: str | None) -> bool:
    return raw is None or raw.strip().lower() in _EMPTY_MARKERS


def phone_digits(raw: str | None) -> str | None:
    """The last ten digits of a phone number, for matching "+1 (555) 010-2030"
    against "5550102030". None when too short to identify anyone."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits[-10:] if len(digits) >= 7 else None


# The format that last parsed successfully. A file almost always uses one date
# format throughout, so trying it first turns ~20 failed attempts per value
# into one successful one -- a large share of the check's time on big files.
_last_format: str | None = None


def _strptime(text: str, formats: tuple[str, ...]) -> datetime | None:
    global _last_format
    if _last_format is not None:
        try:
            return datetime.strptime(text, _last_format)
        except ValueError:
            pass
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        _last_format = fmt
        return parsed
    return None


def _parse_date(text: str) -> date:
    parsed = _strptime(text, _DATE_FORMATS + _DATETIME_FORMATS)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise FieldError from None
    return parsed.date()


def _parse_datetime(text: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = _strptime(text, _DATETIME_FORMATS + _DATE_FORMATS)
    if parsed is None:
        raise FieldError
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def convert(f: Field, raw: str | None):
    """`raw` as this field's type; None when empty. Raises FieldError."""
    if is_empty(raw):
        if f.required:
            raise FieldError(f"{f.label} is required.")
        return None
    text = raw.strip()

    if f.kind in ("text", "note"):
        if f.max_length and len(text) > f.max_length:
            raise FieldError(f"{f.label} is longer than {f.max_length} characters.")
        return text
    if f.kind == "email":
        value = text.lower()
        if not _EMAIL_RE.match(value):
            raise FieldError(f"{f.label} '{text}' is not a valid email address.")
        if f.max_length and len(value) > f.max_length:
            raise FieldError(f"{f.label} is longer than {f.max_length} characters.")
        return value
    if f.kind == "phone":
        if f.max_length and len(text) > f.max_length:
            raise FieldError(f"{f.label} is longer than {f.max_length} characters.")
        return text
    if f.kind in ("int", "decimal"):
        cleaned = re.sub(r"[,$€£₹\s]", "", text)
        try:
            number = Decimal(cleaned)
        except InvalidOperation:
            raise FieldError(f"{f.label} must be a number, got '{text}'.") from None
        if f.kind == "int":
            if number != number.to_integral_value():
                raise FieldError(f"{f.label} must be a whole number, got '{text}'.")
            return int(number)
        return number
    if f.kind == "bool":
        lowered = text.lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        raise FieldError(f"{f.label} must be yes or no, got '{text}'.")
    if f.kind == "date":
        try:
            return _parse_date(text)
        except FieldError:
            raise FieldError(f"{f.label} '{text}' is not a date this import understands (try YYYY-MM-DD).") from None
    if f.kind == "datetime":
        try:
            return _parse_datetime(text)
        except FieldError:
            raise FieldError(f"{f.label} '{text}' is not a date this import understands (try YYYY-MM-DD).") from None
    if f.kind == "list":
        parts = [p.strip() for p in re.split(r"[,;|\n]", text)]
        return [p for p in dict.fromkeys(parts) if p]
    if f.kind == "choice":
        for choice in f.choices:
            if choice.lower() == text.lower():
                return choice
        # Not an error: exported systems have statuses of their own, and losing
        # the record over one would be worse. The caller records a warning.
        return _UnknownChoice(text, f.default)
    raise AssertionError(f"unknown field kind {f.kind}")


@dataclass(frozen=True)
class _UnknownChoice:
    raw: str
    fallback: str | None


def is_unknown_choice(value) -> bool:
    return isinstance(value, _UnknownChoice)
