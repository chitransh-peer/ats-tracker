from app.core.enums import RoleName


def test_recruiter_cannot_list_users(client, make_user, auth_headers):
    """Recruiters have operational access to jobs/candidates/applications, but user
    account management is an Admin/Super Admin/Executive concern per the role matrix."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    response = client.get("/api/v1/users", headers=headers)

    assert response.status_code == 403


def test_candidate_cannot_list_users(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(user.email, password)

    response = client.get("/api/v1/users", headers=headers)

    assert response.status_code == 403


def test_interviewer_cannot_create_user_invitation(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.INTERVIEWER.value])
    headers = auth_headers(user.email, password)

    response = client.post(
        "/api/v1/users", json={"email": "new@example.com", "role_name": RoleName.RECRUITER.value}, headers=headers
    )

    assert response.status_code == 403


def test_admin_can_invite_user(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    response = client.post(
        "/api/v1/users",
        json={"email": "brand-new-invitee@example.com", "role_name": RoleName.RECRUITER.value},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["email"] == "brand-new-invitee@example.com"


def test_super_admin_can_assign_roles(client, make_user, auth_headers):
    admin_user, admin_password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    target_user, _ = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(admin_user.email, admin_password)

    response = client.post(
        f"/api/v1/users/{target_user.id}/roles",
        json={"role_names": [RoleName.RECRUITER.value]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["roles"] == [RoleName.RECRUITER.value]


def test_hiring_manager_cannot_assign_roles(client, make_user, auth_headers):
    hm_user, hm_password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    target_user, _ = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(hm_user.email, hm_password)

    response = client.post(
        f"/api/v1/users/{target_user.id}/roles",
        json={"role_names": [RoleName.RECRUITER.value]},
        headers=headers,
    )

    assert response.status_code == 403


def test_executive_has_read_only_access(client, make_user, auth_headers):
    exec_user, exec_password = make_user(role_names=[RoleName.EXECUTIVE.value])
    headers = auth_headers(exec_user.email, exec_password)

    read_response = client.get("/api/v1/users", headers=headers)
    write_response = client.post(
        "/api/v1/users", json={"email": "blocked@example.com", "role_name": RoleName.RECRUITER.value}, headers=headers
    )

    assert read_response.status_code == 200
    assert write_response.status_code == 403
