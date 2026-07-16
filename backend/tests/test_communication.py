from app.core.enums import RoleName


def test_create_and_list_templates(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    created = client.post(
        "/api/v1/templates",
        json={
            "name": "Application Acknowledgment",
            "type": "Acknowledgment",
            "subject": "We received your application",
            "body": "Hi {{candidate_first_name}}, thanks for applying.",
        },
        headers=headers,
    )
    assert created.status_code == 201

    listed = client.get("/api/v1/templates", headers=headers)
    assert listed.status_code == 200
    assert any(t["name"] == "Application Acknowledgment" for t in listed.json())


def test_send_message_logs_to_candidate_timeline(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    sent = client.post(
        f"/api/v1/candidates/{candidate.id}/messages",
        json={"subject": "Interview scheduled", "body": "Looking forward to speaking with you."},
        headers=headers,
    )
    assert sent.status_code == 201
    assert sent.json()["status"] == "logged"

    listed = client.get(f"/api/v1/candidates/{candidate.id}/messages", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
