"""The remaining findings from the security review, one test per finding."""

import io

from pypdf import PdfWriter
from sqlalchemy import select

from app.core.enums import CandidateDocumentType, JobStatus, RoleName
from app.db.models.ai import ResumeParseRun
from app.db.models.candidate import CandidateDocument
from app.services.ai import evaluation as evaluation_service
from app.services.ai import resume_parsing as resume_parsing_service
from app.services.candidates.service import add_document


def test_a_hiring_manager_cannot_read_ai_scores_for_someone_elses_job(
    client, db, make_user, make_job, make_candidate, make_application, auth_headers
):
    hm, password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    other_hm, _ = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    headers = auth_headers(hm.email, password)

    mine = make_application(candidate=make_candidate(), job=make_job(hiring_manager_id=hm.id))
    theirs = make_application(candidate=make_candidate(), job=make_job(hiring_manager_id=other_hm.id))
    evaluations = {}
    for application in (mine, theirs):
        evaluations[application.id] = evaluation_service.create_pending_evaluation(
            db, organization_id=application.organization_id, application_id=application.id, actor_id=None
        )

    assert client.get(f"/api/v1/applications/{mine.id}/ai-review", headers=headers).status_code == 200
    assert client.get(f"/api/v1/applications/{theirs.id}/ai-review", headers=headers).status_code == 404
    assert client.get(f"/api/v1/ai/evaluations/{evaluations[mine.id].id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/ai/evaluations/{evaluations[theirs.id].id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/ai/compare/jd-resume/{theirs.id}", headers=headers).status_code == 404


def test_the_candidate_role_sees_published_jobs_only(client, make_user, make_job, auth_headers):
    user, password = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(user.email, password)
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)

    draft = make_job(title="Draft Role")
    published = make_job(title="Published Role")
    client.post(f"/api/v1/jobs/{published.id}/publish", headers=recruiter_headers)

    listed = {j["id"] for j in client.get("/api/v1/jobs", headers=headers).json()}

    assert str(published.id) in listed
    assert str(draft.id) not in listed
    assert client.get(f"/api/v1/jobs/{draft.id}", headers=headers).status_code == 404


def test_the_candidate_role_sees_and_files_only_its_own_applications(
    client, db, make_user, make_job, make_candidate, make_application, auth_headers
):
    user, password = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(user.email, password)
    me = make_candidate(email=user.email.upper())  # matched regardless of case
    someone_else = make_candidate()
    job = make_job()
    job.status = JobStatus.ACTIVE.value
    db.commit()

    my_application = make_application(candidate=me, job=make_job())
    their_application = make_application(candidate=someone_else, job=make_job())

    listed = {a["id"] for a in client.get("/api/v1/applications", headers=headers).json()}
    assert str(my_application.id) in listed
    assert str(their_application.id) not in listed

    as_someone_else = client.post(
        "/api/v1/applications", json={"candidate_id": str(someone_else.id), "job_id": str(job.id)}, headers=headers
    )
    assert as_someone_else.status_code == 404
    as_me = client.post("/api/v1/applications", json={"candidate_id": str(me.id), "job_id": str(job.id)}, headers=headers)
    assert as_me.status_code == 201


def test_a_deactivated_user_loses_access_on_the_next_request(client, db, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    assert client.get("/api/v1/jobs", headers=headers).status_code == 200

    user.is_active = False
    db.commit()

    response = client.get("/api/v1/jobs", headers=headers)
    assert response.status_code == 401
    assert "no longer active" in response.text


def test_a_careers_page_upload_cannot_replace_an_existing_candidates_resume(
    client, db, make_user, make_candidate, auth_headers, organization
):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)
    job = client.post(
        "/api/v1/jobs", json={"title": "Portal Role", "workplace": "Remote", "employment_type": "Contract"}, headers=headers
    ).json()
    client.post(f"/api/v1/jobs/{job['id']}/publish", headers=headers)
    existing = make_candidate(email="known.person@example.com")

    response = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{job['id']}/apply",
        data={"full_name": "Not Them", "email": "known.person@example.com"},
        files={"resume": ("resume.pdf", _blank_pdf(), "application/pdf")},
    )

    assert response.status_code == 201
    documents = list(db.scalars(select(CandidateDocument).where(CandidateDocument.candidate_id == existing.id)).all())
    assert len(documents) == 1
    assert documents[0].document_type == CandidateDocumentType.OTHER.value
    assert documents[0].file_name.startswith("Unverified careers-page upload")
    runs = db.scalars(select(ResumeParseRun).where(ResumeParseRun.candidate_id == existing.id)).all()
    assert runs == []


def test_vendor_bank_account_numbers_are_masked(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    created = client.post(
        "/api/v1/vendors",
        json={
            "name": "Masked Bank Vendor",
            "bank_accounts": [
                {"account_holder_name": "Vendor Inc.", "bank_name": "Chase", "account_number": "123456789012"}
            ],
        },
        headers=headers,
    ).json()

    shown = client.get(f"/api/v1/vendors/{created['id']}", headers=headers).json()["bank_accounts"][0]["account_number"]

    assert shown.endswith("9012")
    assert "12345678" not in shown
    assert "123456789012" not in client.get("/api/v1/vendors", headers=headers).text


def test_an_unreadable_pdf_fails_the_parse_with_a_reason(db, make_candidate):
    candidate = make_candidate()
    document = add_document(
        db,
        candidate,
        document_type=CandidateDocumentType.RESUME.value,
        file_name="broken.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4\n this is not really a pdf",
        uploaded_by=None,
    )
    run = resume_parsing_service.create_pending_run(
        db, organization_id=candidate.organization_id, candidate_id=candidate.id, document_id=document.id
    )

    run = resume_parsing_service.parse_resume(db, run)

    assert run.status == "failed"
    assert "could not be read" in run.error_message


def test_legacy_doc_files_are_refused_with_a_reason():
    try:
        resume_parsing_service.extract_text("application/msword", b"\xd0\xcf\x11\xe0 binary")
    except resume_parsing_service.UnreadableResumeError as exc:
        assert ".doc" in str(exc)
    else:
        raise AssertionError("expected UnreadableResumeError")


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
