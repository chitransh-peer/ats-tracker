from app.core.enums import RoleName


def _job_payload(**overrides):
    payload = {
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "Remote",
        "workplace": "Remote",
        "employment_type": "Full-time",
        "openings": 2,
        "pay_min": 100000,
        "pay_max": 150000,
        "priority": "High",
        "summary": "Build the ATS backend",
        "description": "Full description here",
        "responsibilities": ["Ship features"],
        "required_skills": ["Python", "FastAPI"],
        "nice_to_have": ["Docker"],
        "screening_questions": ["Are you authorized to work?"],
        "experience": "3-5 years",
        "education": "Bachelor's degree",
    }
    payload.update(overrides)
    return payload


def test_admin_can_create_job(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    response = client.post("/api/v1/jobs", json=_job_payload(), headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Draft"
    assert body["req_id"].startswith("REQ-")
    assert body["slug"].startswith("senior-backend-engineer-")
    assert body["applications_count"] == 0


def test_candidate_role_cannot_create_job(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(user.email, password)

    response = client.post("/api/v1/jobs", json=_job_payload(), headers=headers)

    assert response.status_code == 403


def test_publish_job_sets_active_and_posted_at(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    created = client.post("/api/v1/jobs", json=_job_payload(), headers=headers).json()
    assert created["posted_at"] is None

    published = client.post(f"/api/v1/jobs/{created['id']}/publish", headers=headers)

    assert published.status_code == 200
    body = published.json()
    assert body["status"] == "Active"
    assert body["posted_at"] is not None


def test_cannot_republish_closed_job(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    created = client.post("/api/v1/jobs", json=_job_payload(), headers=headers).json()
    client.post(f"/api/v1/jobs/{created['id']}/publish", headers=headers)
    closed = client.post(f"/api/v1/jobs/{created['id']}/close", headers=headers)
    assert closed.status_code == 200
    assert closed.json()["status"] == "Closed"

    reopened = client.post(f"/api/v1/jobs/{created['id']}/publish", headers=headers)
    assert reopened.status_code == 422


def test_list_jobs_filters_by_status(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    job_a = client.post("/api/v1/jobs", json=_job_payload(title="Job A"), headers=headers).json()
    client.post("/api/v1/jobs", json=_job_payload(title="Job B"), headers=headers)
    client.post(f"/api/v1/jobs/{job_a['id']}/publish", headers=headers)

    active = client.get("/api/v1/jobs", params={"status": "Active"}, headers=headers)
    draft = client.get("/api/v1/jobs", params={"status": "Draft"}, headers=headers)

    assert active.status_code == 200
    assert {j["id"] for j in active.json()} == {job_a["id"]}
    assert len(draft.json()) == 1
