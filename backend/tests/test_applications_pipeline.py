from app.core.enums import RoleName


def test_create_application_starts_at_first_stage(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()

    response = client.post(
        "/api/v1/applications", json={"candidate_id": str(candidate.id), "job_id": str(job.id)}, headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Active"
    assert body["current_stage_id"] is not None


def test_duplicate_application_is_rejected(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()
    payload = {"candidate_id": str(candidate.id), "job_id": str(job.id)}

    first = client.post("/api/v1/applications", json=payload, headers=headers)
    second = client.post("/api/v1/applications", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def _get_stage_id_by_name(client, headers, name: str) -> str:
    stages = client.get("/api/v1/pipeline/stages", headers=headers).json()["stages"]
    return next(s["id"] for s in stages if s["name"] == name)


def test_move_stage_success(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()
    application = client.post(
        "/api/v1/applications", json={"candidate_id": str(candidate.id), "job_id": str(job.id)}, headers=headers
    ).json()

    screening_stage_id = _get_stage_id_by_name(client, headers, "Screening")
    response = client.post(
        f"/api/v1/applications/{application['id']}/move-stage",
        json={"to_stage_id": screening_stage_id, "note": "Looks good"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["current_stage_id"] == screening_stage_id

    timeline = client.get(f"/api/v1/applications/{application['id']}/timeline", headers=headers)
    assert timeline.status_code == 200
    assert len(timeline.json()) == 2


def test_move_stage_to_hired_marks_application_hired(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()
    application = client.post(
        "/api/v1/applications", json={"candidate_id": str(candidate.id), "job_id": str(job.id)}, headers=headers
    ).json()

    hired_stage_id = _get_stage_id_by_name(client, headers, "Hired")
    response = client.post(
        f"/api/v1/applications/{application['id']}/move-stage", json={"to_stage_id": hired_stage_id}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Hired"


def test_reject_application(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()
    application = client.post(
        "/api/v1/applications", json={"candidate_id": str(candidate.id), "job_id": str(job.id)}, headers=headers
    ).json()

    response = client.post(f"/api/v1/applications/{application['id']}/reject", json={}, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "Rejected"


def test_cannot_move_stage_after_rejection(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()
    application = client.post(
        "/api/v1/applications", json={"candidate_id": str(candidate.id), "job_id": str(job.id)}, headers=headers
    ).json()
    client.post(f"/api/v1/applications/{application['id']}/reject", json={}, headers=headers)

    screening_stage_id = _get_stage_id_by_name(client, headers, "Screening")
    response = client.post(
        f"/api/v1/applications/{application['id']}/move-stage",
        json={"to_stage_id": screening_stage_id},
        headers=headers,
    )

    assert response.status_code == 422


def test_hold_and_restore_application(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job()
    candidate = make_candidate()
    application = client.post(
        "/api/v1/applications", json={"candidate_id": str(candidate.id), "job_id": str(job.id)}, headers=headers
    ).json()

    held = client.post(f"/api/v1/applications/{application['id']}/hold", json={}, headers=headers)
    assert held.status_code == 200
    assert held.json()["status"] == "On Hold"

    restored = client.post(f"/api/v1/applications/{application['id']}/restore", json={}, headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "Active"


def test_interviewer_cannot_move_stage(client, make_user, make_job, make_candidate, auth_headers):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    interviewer, interviewer_password = make_user(role_names=[RoleName.INTERVIEWER.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)
    interviewer_headers = auth_headers(interviewer.email, interviewer_password)
    job = make_job()
    candidate = make_candidate()
    application = client.post(
        "/api/v1/applications",
        json={"candidate_id": str(candidate.id), "job_id": str(job.id)},
        headers=recruiter_headers,
    ).json()

    screening_stage_id = _get_stage_id_by_name(client, recruiter_headers, "Screening")
    response = client.post(
        f"/api/v1/applications/{application['id']}/move-stage",
        json={"to_stage_id": screening_stage_id},
        headers=interviewer_headers,
    )

    assert response.status_code == 403
