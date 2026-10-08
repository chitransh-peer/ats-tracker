"""In-app previews of stored documents, for reading a résumé without
downloading it.

A preview never hands back the original file. PDFs are rendered to page images
on the server, Word documents are reduced to their text, and only plain images
pass through (re-served as what they are). So a user who may view documents
but not download them gets something to read on screen, while the file itself
-- its embedded text layer, metadata and the rest -- stays on the server.
"""

import io
import struct
import zlib
from typing import Literal

from pydantic import BaseModel

# Enough for any résumé or supporting document; a 300-page upload is not
# rendered whole on every view.
MAX_PAGES = 15
# 1.5x of PDF points (72 dpi) is ~108 dpi: crisp text on screen, modest PNGs.
RENDER_SCALE = 1.5
MAX_TEXT_BLOCKS = 2000

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class PreviewBlock(BaseModel):
    kind: Literal["heading", "paragraph", "table"]
    text: str | None = None
    rows: list[list[str]] | None = None


class PreviewPage(BaseModel):
    content_type: str
    data: bytes  # serialized as base64 by the route


class DocumentPreview(BaseModel):
    kind: Literal["pages", "text", "unsupported"]
    file_name: str
    page_count: int = 0
    truncated: bool = False
    pages: list[PreviewPage] = []
    blocks: list[PreviewBlock] = []
    message: str | None = None


def _png(width: int, height: int, stride: int, rgb: bytes) -> bytes:
    """A PNG of a packed RGB buffer, written by hand so no imaging library is
    needed just to put rendered pages on the wire."""
    row_bytes = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride : y * stride + row_bytes] for y in range(height))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


def _pdf_preview(data: bytes, file_name: str) -> DocumentPreview:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    try:
        total = len(pdf)
        pages: list[PreviewPage] = []
        for index in range(min(total, MAX_PAGES)):
            page = pdf[index]
            try:
                # rev_byteorder gives RGB rather than pdfium's native BGR.
                bitmap = page.render(scale=RENDER_SCALE, rev_byteorder=True)
                try:
                    if bitmap.n_channels != 3:
                        raise ValueError("unexpected bitmap format")
                    png = _png(bitmap.width, bitmap.height, bitmap.stride, bytes(bitmap.buffer))
                finally:
                    bitmap.close()
            finally:
                page.close()
            pages.append(PreviewPage(content_type="image/png", data=png))
    finally:
        pdf.close()
    return DocumentPreview(kind="pages", file_name=file_name, page_count=total, truncated=total > MAX_PAGES, pages=pages)


def _docx_preview(data: bytes, file_name: str) -> DocumentPreview:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(io.BytesIO(data))
    blocks: list[PreviewBlock] = []
    # Body order, so tables sit between the paragraphs they came between.
    for child in document.element.body.iterchildren():
        if len(blocks) >= MAX_TEXT_BLOCKS:
            break
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if not text:
                continue
            style = (paragraph.style.name if paragraph.style is not None else "") or ""
            kind = "heading" if style.lower().startswith(("heading", "title")) else "paragraph"
            blocks.append(PreviewBlock(kind=kind, text=text))
        elif tag == "tbl":
            table = Table(child, document)
            rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            rows = [r for r in rows if any(r)]
            if rows:
                blocks.append(PreviewBlock(kind="table", rows=rows))
    return DocumentPreview(kind="text", file_name=file_name, blocks=blocks, truncated=len(blocks) >= MAX_TEXT_BLOCKS)


def _plain_text_preview(data: bytes, file_name: str) -> DocumentPreview:
    text = data.decode("utf-8", errors="replace")
    blocks = [PreviewBlock(kind="paragraph", text=line) for line in text.splitlines() if line.strip()]
    return DocumentPreview(
        kind="text", file_name=file_name, blocks=blocks[:MAX_TEXT_BLOCKS], truncated=len(blocks) > MAX_TEXT_BLOCKS
    )


def _kind_of(file_name: str, content_type: str) -> str:
    name = file_name.lower()
    content_type = (content_type or "").lower().split(";")[0].strip()
    if content_type == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if content_type == _DOCX_TYPE or name.endswith(".docx"):
        return "docx"
    if content_type == "text/plain" or name.endswith(".txt"):
        return "text"
    if content_type in _IMAGE_TYPES:
        return "image"
    return "other"


def build_preview(data: bytes, *, file_name: str, content_type: str) -> DocumentPreview:
    """A preview of a stored file, or an "unsupported" answer saying why not."""
    kind = _kind_of(file_name, content_type)
    try:
        if kind == "pdf":
            return _pdf_preview(data, file_name)
        if kind == "docx":
            return _docx_preview(data, file_name)
        if kind == "text":
            return _plain_text_preview(data, file_name)
        if kind == "image":
            return DocumentPreview(
                kind="pages",
                file_name=file_name,
                page_count=1,
                pages=[PreviewPage(content_type=content_type.split(";")[0].strip().lower(), data=data)],
            )
    except Exception:  # noqa: BLE001 -- a malformed upload gets a message, not a 500
        return DocumentPreview(kind="unsupported", file_name=file_name, message="This file could not be read for preview.")
    return DocumentPreview(
        kind="unsupported",
        file_name=file_name,
        message="Preview is available for PDF, Word (.docx), text and image files.",
    )
