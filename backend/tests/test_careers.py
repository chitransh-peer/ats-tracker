from app.core.enums import RoleName


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

    published = _publish_job(client, headers, title="Published Role")
    client.post("/api/v1/jobs", json={"title": "Draft Role", "workplace": "Remote", "employment_type": "Full-time"}, headers=headers)

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
        data={"full_name": "Casey Public", "email": "casey.public@example.com", "phone": "+1-555-9999"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Active"

    admin_candidates = client.get("/api/v1/candidates", headers=headers).json()
    assert any(c["email"] == "casey.public@example.com" for c in admin_candidates)


def test_second_application_reuses_existing_candidate(client, make_user, auth_headers, organization):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job_a = _publish_job(client, headers, title="Role A")
    job_b = _publish_job(client, headers, title="Role B")

    client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{job_a['id']}/apply",
        data={"full_name": "Casey Public", "email": "casey.repeat@example.com"},
    )
    second = client.post(
        f"/api/v1/careers/{organization.slug}/jobs/{job_b['id']}/apply",
        data={"full_name": "Casey Public", "email": "casey.repeat@example.com"},
    )

    assert second.status_code == 201
    candidates = client.get("/api/v1/candidates", headers=headers).json()
    matching = [c for c in candidates if c["email"] == "casey.repeat@example.com"]
    assert len(matching) == 1


def test_careers_page_404_for_unknown_org(client):
    response = client.get("/api/v1/careers/does-not-exist/jobs")

    assert response.status_code == 404
