from app.core.enums import RoleName


def test_admin_can_read_audit_logs(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    client.post(
        "/api/v1/jobs",
        json={"title": "Audit Test Job", "workplace": "Remote", "employment_type": "Full-time"},
        headers=headers,
    )

    response = client.get("/api/v1/audit-logs", headers=headers)

    assert response.status_code == 200
    assert any(entry["action"] == "job_created" for entry in response.json())


def test_recruiter_cannot_read_audit_logs(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    response = client.get("/api/v1/audit-logs", headers=headers)

    assert response.status_code == 403
