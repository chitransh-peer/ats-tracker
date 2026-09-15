from app.core.enums import RoleName


def _create_offer(client, headers, application_id, **overrides):
    payload = {"application_id": str(application_id), "base_salary": 120000, "bonus": 10000, "equity": "1000 RSUs"}
    payload.update(overrides)
    return client.post("/api/v1/offers", json=payload, headers=headers).json()


def test_recruiter_can_create_offer(client, make_user, make_job, make_candidate, make_application, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())

    offer = _create_offer(client, headers, application.id)

    assert offer["status"] == "Draft"
    assert len(offer["versions"]) == 1
    assert offer["versions"][0]["version_number"] == 1


def test_update_offer_creates_new_version(client, make_user, make_job, make_candidate, make_application, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())
    offer = _create_offer(client, headers, application.id)

    response = client.patch(f"/api/v1/offers/{offer['id']}", json={"base_salary": 135000}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["base_salary"] == 135000
    assert len(body["versions"]) == 2


def test_full_approval_flow(client, make_user, make_job, make_candidate, make_application, auth_headers):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)
    admin_headers = auth_headers(admin.email, admin_password)
    application = make_application(candidate=make_candidate(), job=make_job())
    offer = _create_offer(client, recruiter_headers, application.id)

    submitted = client.post(f"/api/v1/offers/{offer['id']}/submit-approval", json={}, headers=recruiter_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "Approval Pending"

    denied_approve = client.post(f"/api/v1/offers/{offer['id']}/approve", json={}, headers=recruiter_headers)
    assert denied_approve.status_code == 403

    approved = client.post(f"/api/v1/offers/{offer['id']}/approve", json={}, headers=admin_headers)
    assert approved.status_code == 200

    sent = client.post(f"/api/v1/offers/{offer['id']}/send", headers=recruiter_headers)
    assert sent.status_code == 200
    assert sent.json()["status"] == "Sent"

    accepted = client.post(f"/api/v1/offers/{offer['id']}/accept", headers=recruiter_headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "Accepted"


def test_cannot_send_before_approval(client, make_user, make_job, make_candidate, make_application, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())
    offer = _create_offer(client, headers, application.id)

    response = client.post(f"/api/v1/offers/{offer['id']}/send", headers=headers)

    assert response.status_code == 422


def test_reject_returns_offer_to_draft(client, make_user, make_job, make_candidate, make_application, auth_headers):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])
    recruiter_headers = auth_headers(recruiter.email, recruiter_password)
    admin_headers = auth_headers(admin.email, admin_password)
    application = make_application(candidate=make_candidate(), job=make_job())
    offer = _create_offer(client, recruiter_headers, application.id)
    client.post(f"/api/v1/offers/{offer['id']}/submit-approval", json={}, headers=recruiter_headers)

    response = client.post(f"/api/v1/offers/{offer['id']}/reject", json={"note": "Salary too high"}, headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "Draft"
