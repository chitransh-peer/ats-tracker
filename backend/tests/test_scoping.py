from app.core.enums import RoleName


def test_hiring_manager_sees_only_own_job(client, make_user, make_job, auth_headers):
    hm, hm_password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    other_hm, _ = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    headers = auth_headers(hm.email, hm_password)

    my_job = make_job(title="My Job", hiring_manager_id=hm.id)
    other_job = make_job(title="Other Job", hiring_manager_id=other_hm.id)

    listed = client.get("/api/v1/jobs", headers=headers)
    assert listed.status_code == 200
    listed_ids = {j["id"] for j in listed.json()}
    assert str(my_job.id) in listed_ids
    assert str(other_job.id) not in listed_ids

    assert client.get(f"/api/v1/jobs/{my_job.id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/jobs/{other_job.id}", headers=headers).status_code == 404


def test_hiring_manager_scoped_candidates_and_applications(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    hm, hm_password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    other_hm, _ = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    headers = auth_headers(hm.email, hm_password)

    my_job = make_job(hiring_manager_id=hm.id)
    other_job = make_job(hiring_manager_id=other_hm.id)
    my_candidate = make_candidate()
    other_candidate = make_candidate()
    my_application = make_application(candidate=my_candidate, job=my_job)
    other_application = make_application(candidate=other_candidate, job=other_job)

    assert client.get(f"/api/v1/candidates/{my_candidate.id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/candidates/{other_candidate.id}", headers=headers).status_code == 404

    assert client.get(f"/api/v1/applications/{my_application.id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/applications/{other_application.id}", headers=headers).status_code == 404

    applications = client.get("/api/v1/applications", headers=headers).json()
    application_ids = {a["id"] for a in applications}
    assert str(my_application.id) in application_ids
    assert str(other_application.id) not in application_ids


def test_interviewer_sees_only_assigned_interview(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    interviewer, interviewer_password = make_user(role_names=[RoleName.INTERVIEWER.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)
    interviewer_headers = auth_headers(interviewer.email, interviewer_password)

    assigned_application = make_application(candidate=make_candidate(), job=make_job())
    other_application = make_application(candidate=make_candidate(), job=make_job())

    assigned_interview = client.post(
        "/api/v1/interviews",
        json={
            "application_id": str(assigned_application.id),
            "round_name": "Technical",
            "mode": "Video",
            "scheduled_at": "2026-08-01T10:00:00Z",
            "panel_user_ids": [str(interviewer.id)],
            "primary_interviewer_id": str(interviewer.id),
        },
        headers=recruiter_headers,
    ).json()
    other_interview = client.post(
        "/api/v1/interviews",
        json={
            "application_id": str(other_application.id),
            "round_name": "Technical",
            "mode": "Video",
            "scheduled_at": "2026-08-01T10:00:00Z",
        },
        headers=recruiter_headers,
    ).json()

    assert client.get(f"/api/v1/interviews/{assigned_interview['id']}", headers=interviewer_headers).status_code == 200
    assert client.get(f"/api/v1/interviews/{other_interview['id']}", headers=interviewer_headers).status_code == 404

    listed = client.get("/api/v1/interviews", headers=interviewer_headers).json()
    listed_ids = {i["id"] for i in listed}
    assert assigned_interview["id"] in listed_ids
    assert other_interview["id"] not in listed_ids

    # Interviewer also gains visibility into the candidate/application tied to their assigned interview.
    assert client.get(f"/api/v1/applications/{assigned_application.id}", headers=interviewer_headers).status_code == 200
    assert client.get(f"/api/v1/applications/{other_application.id}", headers=interviewer_headers).status_code == 404


def test_recruiter_and_admin_remain_unscoped(client, make_user, make_job, auth_headers):
    hm, _ = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    job_a = make_job(title="Job A", hiring_manager_id=hm.id)
    job_b = make_job(title="Job B", hiring_manager_id=None)

    for role in (RoleName.RECRUITER.value, RoleName.ADMIN.value, RoleName.EXECUTIVE.value, RoleName.SUPER_ADMIN.value):
        user, password = make_user(role_names=[role])
        headers = auth_headers(user.email, password)
        listed_ids = {j["id"] for j in client.get("/api/v1/jobs", headers=headers).json()}
        assert str(job_a.id) in listed_ids
        assert str(job_b.id) in listed_ids
        assert client.get(f"/api/v1/jobs/{job_a.id}", headers=headers).status_code == 200
        assert client.get(f"/api/v1/jobs/{job_b.id}", headers=headers).status_code == 200
