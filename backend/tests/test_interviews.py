from app.core.enums import RoleName


def test_recruiter_can_schedule_interview(client, make_user, make_job, make_candidate, make_application, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())

    response = client.post(
        "/api/v1/interviews",
        json={
            "application_id": str(application.id),
            "round_name": "Technical Assessment",
            "mode": "Video",
            "scheduled_at": "2026-08-01T10:00:00Z",
            "panel_user_ids": [str(user.id)],
            "primary_interviewer_id": str(user.id),
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Scheduled"
    assert body["panel_members"][0]["is_primary"] is True


def test_interviewer_cannot_create_interview(client, make_user, make_job, make_candidate, make_application, auth_headers):
    user, password = make_user(role_names=[RoleName.INTERVIEWER.value])
    headers = auth_headers(user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())

    response = client.post(
        "/api/v1/interviews",
        json={
            "application_id": str(application.id),
            "round_name": "Panel Interview",
            "mode": "Onsite",
            "scheduled_at": "2026-08-01T10:00:00Z",
        },
        headers=headers,
    )

    assert response.status_code == 403


def test_submit_feedback_and_consolidated_view(client, make_user, make_job, make_candidate, make_application, auth_headers):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    interviewer, interviewer_password = make_user(role_names=[RoleName.INTERVIEWER.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)
    interviewer_headers = auth_headers(interviewer.email, interviewer_password)
    application = make_application(candidate=make_candidate(), job=make_job())

    interview = client.post(
        "/api/v1/interviews",
        json={
            "application_id": str(application.id),
            "round_name": "Recruiter Screen",
            "mode": "Phone",
            "scheduled_at": "2026-08-01T10:00:00Z",
            "panel_user_ids": [str(interviewer.id)],
            "primary_interviewer_id": str(interviewer.id),
        },
        headers=recruiter_headers,
    ).json()

    feedback = client.post(
        f"/api/v1/interviews/{interview['id']}/feedback",
        json={"rating": 4, "recommendation": "Yes", "notes": "Solid communicator"},
        headers=interviewer_headers,
    )
    assert feedback.status_code == 201

    consolidated = client.get(f"/api/v1/interviews/{interview['id']}/consolidated-feedback", headers=recruiter_headers)
    assert consolidated.status_code == 200
    body = consolidated.json()
    assert body["average_rating"] == 4
    assert body["recommendation_counts"] == {"Yes": 1}


def test_update_interview_status(client, make_user, make_job, make_candidate, make_application, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())
    interview = client.post(
        "/api/v1/interviews",
        json={
            "application_id": str(application.id),
            "round_name": "Hiring Manager Interview",
            "mode": "Video",
            "scheduled_at": "2026-08-01T10:00:00Z",
        },
        headers=headers,
    ).json()

    response = client.patch(f"/api/v1/interviews/{interview['id']}", json={"status": "Completed"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "Completed"
