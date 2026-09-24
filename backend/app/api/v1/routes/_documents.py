"""Turning a stored document into an HTTP response.

Shared by the candidate, client, job and vendor document endpoints so the
security-relevant details -- how the filename is quoted, and the fact that
nothing is ever served inline -- are decided once rather than four times.
"""

from urllib.parse import quote

from fastapi import Response

from app.services.storage.service import download_bytes


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
