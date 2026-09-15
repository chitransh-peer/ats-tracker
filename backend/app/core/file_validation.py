"""Validation for user-supplied file uploads — résumés today, and anything
else that ends up going through `upload_bytes` later.

The declared filename and `Content-Type` on a multipart upload are whatever
the client says they are; neither is trustworthy. This checks the file
extension against an allowlist and confirms the actual file content starts
with the magic bytes for that format, rather than trusting either label.
"""

from app.core.exceptions import ValidationAppError

MAX_RESUME_BYTES = 10 * 1024 * 1024  # 10 MB — a résumé has no business being bigger.
# Applies to any candidate document, résumé or not — nothing needs to fill
# the disk regardless of what kind of file it claims to be.
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024

# Extension -> the byte signature(s) a genuine file of that type starts with.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".docx": (b"PK\x03\x04",),  # DOCX is a zip archive (Office Open XML).
    # Legacy .doc is an OLE compound file — same signature Excel/PowerPoint use,
    # so this only confirms "some MS Office binary format", not specifically
    # Word. Good enough to reject an executable or script wearing a .doc name.
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}

_ALLOWED_EXTENSIONS = ", ".join(sorted(_SIGNATURES))


def _extension_of(file_name: str) -> str:
    dot = file_name.rfind(".")
    return file_name[dot:].lower() if dot != -1 else ""


def validate_document_size(*, data: bytes) -> None:
    """Blanket size cap applied to every candidate document upload,
    independent of the format checks below."""
    if len(data) == 0:
        raise ValidationAppError("The uploaded file is empty.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValidationAppError(f"The file is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB.")


def validate_resume_upload(*, data: bytes, file_name: str) -> None:
    """Raises ValidationAppError if `data` isn't a plausible PDF/DOC/DOCX
    within the size limit. Never trusts the caller's declared content-type."""
    if len(data) == 0:
        raise ValidationAppError("The uploaded file is empty.")
    if len(data) > MAX_RESUME_BYTES:
        raise ValidationAppError(
            f"The file is larger than {MAX_RESUME_BYTES // (1024 * 1024)} MB. "
            "Résumés should be well under that — try a plain PDF export."
        )

    extension = _extension_of(file_name)
    signatures = _SIGNATURES.get(extension)
    if signatures is None:
        raise ValidationAppError(
            f"Unsupported file type '{extension or '(none)'}'. Accepted formats: {_ALLOWED_EXTENSIONS}."
        )
    if not any(data.startswith(sig) for sig in signatures):
        raise ValidationAppError(
            f"This file doesn't look like a genuine {extension.lstrip('.').upper()} — "
            "it may be renamed or corrupted. Try re-exporting and uploading again."
        )
