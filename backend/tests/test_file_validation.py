"""Résumé upload validation.

The declared filename and Content-Type on a multipart upload come from the
client and are not trustworthy; these tests confirm the actual bytes are
checked rather than the label the browser attached.
"""

import pytest

from app.core.enums import RoleName
from app.core.exceptions import ValidationAppError
from app.core.file_validation import (
    MAX_DOCUMENT_BYTES,
    MAX_RESUME_BYTES,
    validate_document_size,
    validate_resume_upload,
)

_REAL_PDF = b"%PDF-1.4\n%mock content for a test\n%%EOF"
_REAL_DOCX = b"PK\x03\x04" + b"\x00" * 20  # a real docx is a zip; this is enough for the signature check
_FAKE_PDF = b"<html><script>alert(1)</script></html>"


def test_genuine_pdf_passes():
    validate_resume_upload(data=_REAL_PDF, file_name="resume.pdf")


def test_genuine_docx_passes():
    validate_resume_upload(data=_REAL_DOCX, file_name="resume.docx")


def test_html_renamed_to_pdf_is_rejected():
    """The content-type header is client-supplied and not trusted; only the
    actual bytes decide whether a .pdf is really a PDF."""
    with pytest.raises(ValidationAppError, match="doesn't look like a genuine PDF"):
        validate_resume_upload(data=_FAKE_PDF, file_name="resume.pdf")


def test_unsupported_extension_is_rejected():
    with pytest.raises(ValidationAppError, match="Unsupported file type"):
        validate_resume_upload(data=_REAL_PDF, file_name="resume.exe")


def test_oversized_resume_is_rejected():
    oversized = b"%PDF" + b"0" * (MAX_RESUME_BYTES + 1)
    with pytest.raises(ValidationAppError, match="larger than"):
        validate_resume_upload(data=oversized, file_name="resume.pdf")


def test_empty_upload_is_rejected():
    with pytest.raises(ValidationAppError, match="empty"):
        validate_resume_upload(data=b"", file_name="resume.pdf")


def test_document_size_cap_is_independent_of_format():
    """The generic size cap (for non-résumé documents) doesn't care what the
    content looks like — only how big it is."""
    validate_document_size(data=b"anything at all")
    with pytest.raises(ValidationAppError, match="larger than"):
        validate_document_size(data=b"0" * (MAX_DOCUMENT_BYTES + 1))


# --------------------------------------------------------------------- HTTP


def test_resume_upload_endpoint_rejects_a_fake_pdf(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    response = client.post(
        f"/api/v1/candidates/{candidate.id}/documents",
        files={"file": ("resume.pdf", _FAKE_PDF, "application/pdf")},
        data={"document_type": "resume"},
        headers=headers,
    )

    assert response.status_code == 422
    assert "doesn't look like a genuine PDF" in response.json()["detail"]


def test_resume_upload_endpoint_accepts_a_genuine_pdf(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    response = client.post(
        f"/api/v1/candidates/{candidate.id}/documents",
        files={"file": ("resume.pdf", _REAL_PDF, "application/pdf")},
        data={"document_type": "resume"},
        headers=headers,
    )

    assert response.status_code == 201


def test_non_resume_document_type_is_not_format_restricted(client, make_user, make_candidate, auth_headers):
    """An 'other' document (e.g. a signed offer letter) isn't limited to
    PDF/DOC/DOCX, but still gets the blanket size cap."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    response = client.post(
        f"/api/v1/candidates/{candidate.id}/documents",
        files={"file": ("notes.txt", b"plain text notes", "text/plain")},
        data={"document_type": "other"},
        headers=headers,
    )

    assert response.status_code == 201


def test_careers_apply_rejects_a_fake_resume(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = client.post(
        "/api/v1/jobs",
        json={"title": "Validation Test Role", "workplace": "Remote", "employment_type": "Full-time"},
        headers=headers,
    ).json()
    client.post(f"/api/v1/jobs/{job['id']}/publish", headers=headers)

    response = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{job['id']}/apply",
        data={"full_name": "Applicant", "email": "applicant@example.com"},
        files={"resume": ("resume.pdf", _FAKE_PDF, "application/pdf")},
    )

    assert response.status_code == 422
