from app.core.enums import RoleName


def _accepted_offer(client, headers, admin_headers, application_id):
    """Drive an offer through the full approval flow to Accepted."""
    offer = client.post(
        "/api/v1/offers",
        json={"application_id": str(application_id), "base_salary": 120000},
        headers=headers,
    ).json()
    client.post(f"/api/v1/offers/{offer['id']}/submit-approval", json={}, headers=headers)
    client.post(f"/api/v1/offers/{offer['id']}/approve", json={}, headers=admin_headers)
    client.post(f"/api/v1/offers/{offer['id']}/send", headers=headers)
    accepted = client.post(f"/api/v1/offers/{offer['id']}/accept", headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "Accepted"
    return offer


def test_accepting_offer_opens_onboarding_case_with_default_tasks(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    recruiter, rp = make_user(role_names=[RoleName.RECRUITER.value])
    admin, ap = make_user(role_names=[RoleName.ADMIN.value])
    r_headers = auth_headers(recruiter.email, rp)
    a_headers = auth_headers(admin.email, ap)
    application = make_application(candidate=make_candidate(), job=make_job())

    _accepted_offer(client, r_headers, a_headers, application.id)

    cases = client.get("/api/v1/onboarding", headers=r_headers).json()
    matching = [c for c in cases if c["application_id"] == str(application.id)]
    assert len(matching) == 1
    case = matching[0]
    assert case["status"] == "In Progress"
    assert len(case["tasks"]) == 6
    assert all(t["status"] == "Pending" for t in case["tasks"])


def test_accepting_offer_is_idempotent_for_onboarding(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    recruiter, rp = make_user(role_names=[RoleName.RECRUITER.value])
    admin, ap = make_user(role_names=[RoleName.ADMIN.value])
    r_headers = auth_headers(recruiter.email, rp)
    a_headers = auth_headers(admin.email, ap)
    application = make_application(candidate=make_candidate(), job=make_job())

    _accepted_offer(client, r_headers, a_headers, application.id)
    # A second accept must not create a duplicate case (offer is already Accepted -> 422).
    cases = client.get(f"/api/v1/onboarding?application_id={application.id}", headers=r_headers).json()
    assert len(cases) == 1


def test_completing_case_requires_all_tasks_done_and_hires_candidate(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    recruiter, rp = make_user(role_names=[RoleName.RECRUITER.value])
    admin, ap = make_user(role_names=[RoleName.ADMIN.value])
    r_headers = auth_headers(recruiter.email, rp)
    a_headers = auth_headers(admin.email, ap)
    application = make_application(candidate=make_candidate(), job=make_job())
    _accepted_offer(client, r_headers, a_headers, application.id)

    case = client.get(f"/api/v1/onboarding?application_id={application.id}", headers=r_headers).json()[0]

    # Cannot complete while tasks are still pending.
    premature = client.post(f"/api/v1/onboarding/{case['id']}/complete", headers=r_headers)
    assert premature.status_code == 422

    for task in case["tasks"]:
        resp = client.patch(
            f"/api/v1/onboarding/tasks/{task['id']}",
            json={"status": "Completed"},
            headers=r_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["completed_at"] is not None

    completed = client.post(f"/api/v1/onboarding/{case['id']}/complete", headers=r_headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "Completed"

    apps = client.get(f"/api/v1/applications?candidate_id={application.candidate_id}", headers=r_headers).json()
    assert apps[0]["status"] == "Hired"


def test_add_custom_task_and_update_case(client, make_user, make_job, make_candidate, make_application, auth_headers):
    recruiter, rp = make_user(role_names=[RoleName.RECRUITER.value])
    admin, ap = make_user(role_names=[RoleName.ADMIN.value])
    r_headers = auth_headers(recruiter.email, rp)
    a_headers = auth_headers(admin.email, ap)
    application = make_application(candidate=make_candidate(), job=make_job())
    _accepted_offer(client, r_headers, a_headers, application.id)
    case = client.get(f"/api/v1/onboarding?application_id={application.id}", headers=r_headers).json()[0]

    added = client.post(
        f"/api/v1/onboarding/{case['id']}/tasks",
        json={"title": "Order swag kit", "category": "Equipment"},
        headers=r_headers,
    )
    assert added.status_code == 201

    updated = client.patch(
        f"/api/v1/onboarding/{case['id']}",
        json={"notes": "Remote start"},
        headers=r_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Remote start"
    assert len(updated.json()["tasks"]) == 7


def test_cancel_case(client, make_user, make_job, make_candidate, make_application, auth_headers):
    recruiter, rp = make_user(role_names=[RoleName.RECRUITER.value])
    admin, ap = make_user(role_names=[RoleName.ADMIN.value])
    r_headers = auth_headers(recruiter.email, rp)
    a_headers = auth_headers(admin.email, ap)
    application = make_application(candidate=make_candidate(), job=make_job())
    _accepted_offer(client, r_headers, a_headers, application.id)
    case = client.get(f"/api/v1/onboarding?application_id={application.id}", headers=r_headers).json()[0]

    cancelled = client.post(f"/api/v1/onboarding/{case['id']}/cancel", headers=r_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "Cancelled"

    # A cancelled case can no longer be completed.
    assert client.post(f"/api/v1/onboarding/{case['id']}/complete", headers=r_headers).status_code == 422


def test_interviewer_cannot_read_onboarding(client, make_user, make_job, make_candidate, make_application, auth_headers):
    interviewer, ip = make_user(role_names=[RoleName.INTERVIEWER.value])
    i_headers = auth_headers(interviewer.email, ip)
    resp = client.get("/api/v1/onboarding", headers=i_headers)
    assert resp.status_code == 403
