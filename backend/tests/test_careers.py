import uuid

from app.core.enums import RoleName
from tests.careers_form import application_form, resume_file


def _publish_job(client, headers, **overrides):
    payload = {
        "title": "Product Designer",
        "workplace": "Remote",
        "employment_type": "Full-time",
    }
    payload.update(overrides)
    job = client.post("/api/v1/jobs", json=payload, headers=headers).json()
    client.post(f"/api/v1/jobs/{job['id']}/publish", headers=headers)
    return job


def test_public_job_listing_only_shows_active_jobs(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    _publish_job(client, headers, title="Published Role")
    client.post(
        "/api/v1/jobs", json={"title": "Draft Role", "workplace": "Remote", "employment_type": "Full-time"}, headers=headers
    )

    response = client.get(f"/api/v1/careers/{organization.slug}/jobs")

    assert response.status_code == 200
    titles = {j["title"] for j in response.json()}
    assert "Published Role" in titles
    assert "Draft Role" not in titles


def test_public_job_detail_by_slug(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    published = _publish_job(client, headers)

    response = client.get(f"/api/v1/careers/{organization.slug}/jobs/{published['slug']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Product Designer"


def test_apply_to_job_creates_candidate_and_application(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    published = _publish_job(client, headers)

    response = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{published['id']}/apply",
        data=application_form("Casey Public", "casey.public@example.com", phone="+1-555-9999"),
        files=resume_file(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Active"

    admin_candidates = client.get("/api/v1/candidates", headers=headers).json()
    assert any(c["email"] == "casey.public@example.com" for c in admin_candidates)


def test_an_application_is_scored_without_a_worker(client, db, make_user, auth_headers, organization):
    """No broker is configured here, as on the Cloud Run deployment. Scoring used
    to be skipped outright in that shape, leaving every careers-page applicant
    unscored; it now runs in-process once the response has gone out."""
    from sqlalchemy import select

    from app.core.enums import AIEvaluationStatus
    from app.db.models.ai import AIEvaluation

    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    published = _publish_job(client, auth_headers(user.email, password))

    response = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{published['id']}/apply",
        data=application_form("Scored Applicant", "scored.applicant@example.com"),
        files=resume_file(),
    )

    assert response.status_code == 201
    evaluation = db.scalar(
        select(AIEvaluation).where(AIEvaluation.application_id == uuid.UUID(response.json()["application_id"]))
    )
    # The test environment has no LLM, so this is the rule-based score -- but it
    # is a finished score, not one left pending forever.
    assert evaluation.status == AIEvaluationStatus.COMPLETED.value
    assert evaluation.overall_score is not None


def test_second_application_reuses_existing_candidate(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job_a = _publish_job(client, headers, title="Role A")
    job_b = _publish_job(client, headers, title="Role B")

    client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{job_a['id']}/apply",
        data=application_form("Casey Public", "casey.repeat@example.com"),
        files=resume_file(),
    )
    second = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{job_b['id']}/apply",
        data=application_form("Casey Public", "casey.repeat@example.com"),
        files=resume_file(),
    )

    assert second.status_code == 201
    candidates = client.get("/api/v1/candidates", headers=headers).json()
    matching = [c for c in candidates if c["email"] == "casey.repeat@example.com"]
    assert len(matching) == 1


def test_careers_page_404_for_unknown_org(client):
    response = client.get("/api/v1/careers/does-not-exist/jobs")

    assert response.status_code == 404


def test_job_detail_carries_role_specific_questions(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    designer = _publish_job(client, headers)
    developer = _publish_job(client, headers, title="Backend Developer", screening_questions=["Why us?"])

    design_body = client.get(f"/api/v1/careers/{organization.slug}/jobs/{designer['slug']}").json()
    dev_body = client.get(f"/api/v1/careers/{organization.slug}/jobs/{developer['slug']}").json()

    assert "design_tools" in [q["key"] for q in design_body["role_questions"]]
    assert design_body["ask_portfolio_links"] is True
    dev_keys = [q["key"] for q in dev_body["role_questions"]]
    assert "primary_language" in dev_keys and "design_tools" not in dev_keys
    assert dev_body["role_questions"][-1]["label"] == "Why us?"


def test_application_keeps_answers_and_fills_new_candidate(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    published = _publish_job(client, headers)

    response = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{published['id']}/apply",
        data=application_form("Dana Form", "dana.form@example.com", current_company="Acme"),
        files=resume_file(),
    )

    assert response.status_code == 201
    application = client.get(f"/api/v1/applications/{response.json()['application_id']}", headers=headers).json()
    answered = {a["question"]: a["answer"] for a in application["answers"]}
    assert answered["Which design tools do you use?"] == "Figma"
    assert answered["Notice Period"] == "30 days"
    candidate = client.get(f"/api/v1/candidates/{response.json()['candidate_id']}", headers=headers).json()
    assert candidate["current_company"] == "Acme"
    assert candidate["location"] == "Austin, TX"


def test_application_requires_resume_and_role_answers(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    published = _publish_job(client, auth_headers(user.email, password))
    url = f"/api/v1/careers/{organization.slug}/jobs/{published['id']}/apply"

    no_resume = client.post(url, data=application_form("No Resume", "no.resume@example.com"))
    no_answers = client.post(
        url, data=application_form("No Answers", "no.answers@example.com", role_answers="{}"), files=resume_file()
    )

    assert no_resume.status_code == 422
    assert no_answers.status_code == 422
