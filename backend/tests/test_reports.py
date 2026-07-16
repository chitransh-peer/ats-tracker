from app.core.enums import RoleName


def _stage_id(client, headers, name: str) -> str:
    stages = client.get("/api/v1/pipeline/stages", headers=headers).json()["stages"]
    return next(s["id"] for s in stages if s["name"] == name)


def test_funnel_counts_max_stage_reached(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()

    app1 = client.post(
        "/api/v1/applications", json={"candidate_id": str(make_candidate().id), "job_id": str(job.id)}, headers=headers
    ).json()
    app2 = client.post(
        "/api/v1/applications", json={"candidate_id": str(make_candidate().id), "job_id": str(job.id)}, headers=headers
    ).json()
    app3 = client.post(
        "/api/v1/applications", json={"candidate_id": str(make_candidate().id), "job_id": str(job.id)}, headers=headers
    ).json()

    screening_id = _stage_id(client, headers, "Screening")
    hired_id = _stage_id(client, headers, "Hired")
    client.post(f"/api/v1/applications/{app2['id']}/move-stage", json={"to_stage_id": screening_id}, headers=headers)
    client.post(f"/api/v1/applications/{app3['id']}/move-stage", json={"to_stage_id": hired_id}, headers=headers)

    funnel = client.get("/api/v1/reports/funnel", headers=headers).json()

    by_stage = {row["stage"]: row["value"] for row in funnel}
    assert by_stage["Applied"] == 3
    assert by_stage["Screening"] == 2
    assert by_stage["Hired"] == 1
    assert by_stage["Shortlisted"] == 1


def test_source_effectiveness_groups_by_source(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()

    client.post(
        "/api/v1/applications",
        json={"candidate_id": str(make_candidate().id), "job_id": str(job.id), "source": "LinkedIn"},
        headers=headers,
    )
    client.post(
        "/api/v1/applications",
        json={"candidate_id": str(make_candidate().id), "job_id": str(job.id), "source": "LinkedIn"},
        headers=headers,
    )
    client.post(
        "/api/v1/applications",
        json={"candidate_id": str(make_candidate().id), "job_id": str(job.id), "source": "Referral"},
        headers=headers,
    )

    response = client.get("/api/v1/reports/source-effectiveness", headers=headers)

    by_source = {row["source"]: row["value"] for row in response.json()}
    assert by_source["LinkedIn"] == 2
    assert by_source["Referral"] == 1


def test_aging_jobs_only_lists_active(client, make_user, make_job, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    active_job = make_job(title="Active Role")
    make_job(title="Draft Role")
    client.post(f"/api/v1/jobs/{active_job.id}/publish", headers=headers)

    response = client.get("/api/v1/reports/aging-jobs", headers=headers)

    titles = {row["title"] for row in response.json()}
    assert "Active Role" in titles
    assert "Draft Role" not in titles
    assert all(row["age_days"] is not None for row in response.json())


def test_recruiter_dashboard_scopes_to_current_user(client, make_user, make_job, make_candidate, auth_headers):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)
    job = make_job(recruiter_id=recruiter.id)
    client.post(f"/api/v1/jobs/{job.id}/publish", headers=headers)
    client.post(
        "/api/v1/applications", json={"candidate_id": str(make_candidate().id), "job_id": str(job.id)}, headers=headers
    )

    response = client.get("/api/v1/reports/recruiter-dashboard", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["open_jobs"] == 1
    assert body["applications_this_week"] == 1


def test_executive_dashboard_totals(client, make_user, make_job, make_candidate, auth_headers):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    executive, executive_password = make_user(role_names=[RoleName.EXECUTIVE.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)
    executive_headers = auth_headers(executive.email, executive_password)
    job = make_job()
    client.post(f"/api/v1/jobs/{job.id}/publish", headers=recruiter_headers)
    make_candidate()

    response = client.get("/api/v1/reports/executive-dashboard", headers=executive_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_open_jobs"] == 1
    assert body["total_candidates"] == 1
    assert "funnel" in body
