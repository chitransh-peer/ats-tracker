from app.core.enums import RoleName
from app.core.security import decode_token


def test_super_admin_can_view_as_another_role(client, make_user, auth_headers):
    super_admin, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    headers = auth_headers(super_admin.email, password)

    response = client.post("/api/v1/auth/view-as", json={"role_name": "recruiter"}, headers=headers)

    assert response.status_code == 200
    token = response.json()["access_token"]
    decoded = decode_token(token)
    assert decoded["roles"] == ["recruiter"]
    assert decoded["sub"] == str(super_admin.id)
    assert decoded["impersonating"] is True


def test_view_as_token_reflects_real_permission_restrictions(client, make_user, make_job, auth_headers):
    super_admin, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    real_headers = auth_headers(super_admin.email, password)

    view_as = client.post("/api/v1/auth/view-as", json={"role_name": "executive"}, headers=real_headers)
    view_as_headers = {"Authorization": f"Bearer {view_as.json()['access_token']}"}

    make_job()
    # Executive is read-only — creating a job must be forbidden under the view-as token.
    create_attempt = client.post(
        "/api/v1/jobs",
        json={"title": "Should Fail", "workplace": "Remote", "employment_type": "Full-time"},
        headers=view_as_headers,
    )
    assert create_attempt.status_code == 403

    # But reads still work, proving the token is genuinely usable, not just decorative.
    assert client.get("/api/v1/jobs", headers=view_as_headers).status_code == 200


def test_non_super_admin_cannot_view_as(client, make_user, auth_headers):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)

    response = client.post("/api/v1/auth/view-as", json={"role_name": "admin"}, headers=headers)

    assert response.status_code == 403


def test_view_as_rejects_unknown_role(client, make_user, auth_headers):
    super_admin, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    headers = auth_headers(super_admin.email, password)

    response = client.post("/api/v1/auth/view-as", json={"role_name": "not_a_real_role"}, headers=headers)

    assert response.status_code == 422
