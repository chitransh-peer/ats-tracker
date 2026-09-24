"""Reading a stored document back out.

Uploading was implemented; downloading was not, so a resume could be attached
to a candidate and then never opened again. These cover the round trip and,
more importantly, the scoping: the file has to be exactly as reachable as the
record it hangs off, and no more.
"""

import uuid

from app.core.enums import RoleName


def _upload(client, headers, candidate_id, *, content=b"%PDF-1.4 pretend resume", name="cv.pdf"):
    return client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        files={"file": (name, content, "application/pdf")},
        data={"document_type": "resume"},
        headers=headers,
    )


def test_uploaded_resume_can_be_downloaded_again(client, make_user, auth_headers, make_candidate):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    body = b"%PDF-1.4 pretend resume"
    uploaded = _upload(client, headers, candidate.id, content=body)
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]

    listed = client.get(f"/api/v1/candidates/{candidate.id}/documents", headers=headers)
    assert listed.status_code == 200
    assert [d["id"] for d in listed.json()] == [document_id]

    downloaded = client.get(f"/api/v1/candidates/{candidate.id}/documents/{document_id}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == body


def test_download_is_always_an_attachment(client, make_user, auth_headers, make_candidate):
    """A candidate-supplied file served inline could run script in the app's
    own origin, against the session of whoever opened it."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    document_id = _upload(client, headers, candidate.id).json()["id"]
    response = client.get(f"/api/v1/candidates/{candidate.id}/documents/{document_id}/download", headers=headers)

    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    # Private to the session that asked for it; never a shared cache.
    assert "no-store" in response.headers["cache-control"]


def test_a_document_id_cannot_be_read_through_another_candidate(client, make_user, auth_headers, make_candidate):
    """The lookup is scoped by candidate, not by document id alone -- otherwise
    an id leaked from one record would read a file attached to another."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    owner = make_candidate()
    bystander = make_candidate()
    document_id = _upload(client, headers, owner.id).json()["id"]

    response = client.get(f"/api/v1/candidates/{bystander.id}/documents/{document_id}/download", headers=headers)
    assert response.status_code == 404


def test_unknown_document_is_a_404(client, make_user, auth_headers, make_candidate):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    response = client.get(f"/api/v1/candidates/{candidate.id}/documents/{uuid.uuid4()}/download", headers=headers)
    assert response.status_code == 404


def test_download_is_refused_to_someone_who_cannot_see_the_candidate(client, make_user, auth_headers, make_candidate):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    candidate = make_candidate()
    document_id = _upload(client, auth_headers(recruiter.email, recruiter_password), candidate.id).json()["id"]

    # An interviewer only ever sees candidates they are assigned to, and this
    # one they are not. The refusal is a 404 rather than a 403 because the
    # scoping hides the record itself -- which is the better answer, since a
    # 403 would confirm that this candidate and document exist.
    interviewer, interviewer_password = make_user(role_names=[RoleName.INTERVIEWER.value])
    response = client.get(
        f"/api/v1/candidates/{candidate.id}/documents/{document_id}/download",
        headers=auth_headers(interviewer.email, interviewer_password),
    )
    assert response.status_code == 404
    assert b"pretend resume" not in response.content


def test_download_requires_authentication(client, make_user, auth_headers, make_candidate):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    candidate = make_candidate()
    document_id = _upload(client, auth_headers(user.email, password), candidate.id).json()["id"]

    response = client.get(f"/api/v1/candidates/{candidate.id}/documents/{document_id}/download")
    assert response.status_code == 401


def test_a_non_ascii_filename_survives_the_round_trip(client, make_user, auth_headers, make_candidate):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    document_id = _upload(client, headers, candidate.id, name="Curriculum Vitæ ünïcode.pdf").json()["id"]
    response = client.get(f"/api/v1/candidates/{candidate.id}/documents/{document_id}/download", headers=headers)

    assert response.status_code == 200
    # RFC 6266: the plain filename stays ASCII for old clients, and filename*
    # carries the real one. A header this malformed would break the response.
    disposition = response.headers["content-disposition"]
    assert "filename*=UTF-8''" in disposition
    assert "%C3%A6" in disposition or "%C3%BC" in disposition
