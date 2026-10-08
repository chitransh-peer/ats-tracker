"""Turning a stored document into an HTTP response.

Shared by the candidate, client, job and vendor document endpoints so the
security-relevant details -- how the filename is quoted, the fact that nothing
is ever served inline, and who may take a copy of the file at all -- are
decided once rather than four times.
"""

import base64
from urllib.parse import quote

from fastapi import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.enums import PermissionAction, PermissionResource
from app.core.exceptions import ForbiddenError
from app.schemas.auth import CurrentUser
from app.services.roles.service import roles_grant
from app.services.storage.preview import build_preview
from app.services.storage.service import download_bytes


def can_download_documents(db: Session, user: CurrentUser) -> bool:
    return roles_grant(db, user.roles, PermissionResource.DOCUMENT_DOWNLOAD, PermissionAction.READ)


def ensure_can_download(db: Session, user: CurrentUser) -> None:
    """Downloading the original file is its own permission, held by admins by
    default. Everyone else who can see a record reads its documents through
    the preview instead."""
    if not can_download_documents(db, user):
        raise ForbiddenError("Your role can preview documents but not download them")


def document_response(*, storage_key: str, file_name: str, content_type: str) -> Response:
    """Stream a stored file back to the caller as a download.

    The bytes travel through the API rather than via a signed URL pointing at
    the bucket. That costs a hop, but it means access is decided by the same
    permission check as the record the file hangs off, and there is no URL in
    existence that works for anyone who happens to come across it.

    Content-Disposition is always `attachment`. Serving a candidate-supplied
    file inline would let an uploaded HTML or SVG document execute script in
    the application's origin, against the session of whoever opened it.
    """
    # RFC 6266: a plain filename for old clients, filename* for anything
    # non-ASCII. The quoting matters -- a name containing a quote or newline
    # could otherwise inject a header.
    ascii_name = file_name.encode("ascii", "replace").decode("ascii").replace('"', "'").replace("\\", "_")
    ascii_name = "".join(c for c in ascii_name if c.isprintable())
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name, safe='')}"

    return Response(
        content=download_bytes(storage_key),
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": disposition,
            # The file is only as private as the session that asked for it, so
            # it must not sit in a shared cache.
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


class PreviewPageRead(BaseModel):
    content_type: str
    data_base64: str


class PreviewBlockRead(BaseModel):
    kind: str
    text: str | None = None
    rows: list[list[str]] | None = None


class DocumentPreviewRead(BaseModel):
    kind: str  # "pages" | "text" | "unsupported"
    file_name: str
    page_count: int
    truncated: bool
    pages: list[PreviewPageRead]
    blocks: list[PreviewBlockRead]
    message: str | None
    # Whether this viewer may also download the original, so the viewer can
    # offer the button only to those it will work for.
    can_download: bool


def preview_response(
    db: Session, user: CurrentUser, *, storage_key: str, file_name: str, content_type: str
) -> DocumentPreviewRead:
    """A read-only rendering of a stored file for the in-app viewer: page
    images for PDFs, text for Word files. Never the file itself."""
    preview = build_preview(download_bytes(storage_key), file_name=file_name, content_type=content_type)
    return DocumentPreviewRead(
        kind=preview.kind,
        file_name=preview.file_name,
        page_count=preview.page_count,
        truncated=preview.truncated,
        pages=[
            PreviewPageRead(content_type=p.content_type, data_base64=base64.b64encode(p.data).decode("ascii"))
            for p in preview.pages
        ],
        blocks=[PreviewBlockRead(**b.model_dump()) for b in preview.blocks],
        message=preview.message,
        can_download=can_download_documents(db, user),
    )
