"""The Super Admin role can only be granted, changed or taken away by a Super
Admin. Admins manage users, and without this could promote themselves or lock
the real Super Admin out."""

from app.core.enums import RoleName


def test_admin_cannot_promote_itself(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])

    response = client.post(
        f"/api/v1/users/{admin.id}/roles",
        json={"role_names": [RoleName.SUPER_ADMIN.value]},
        headers=auth_headers(admin.email, password),
    )

    assert response.status_code == 403


def test_admin_cannot_invite_a_super_admin(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])

    response = client.post(
        "/api/v1/users",
        json={"email": "new-owner@example.com", "full_name": "New Owner", "role_name": RoleName.SUPER_ADMIN.value},
        headers=auth_headers(admin.email, password),
    )

    assert response.status_code == 403


def test_admin_cannot_deactivate_a_super_admin(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    owner, _ = make_user(role_names=[RoleName.SUPER_ADMIN.value])

    response = client.patch(
        f"/api/v1/users/{owner.id}", json={"is_active": False}, headers=auth_headers(admin.email, password)
    )

    assert response.status_code == 403


def test_admin_cannot_strip_the_super_admin_role(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    owner, _ = make_user(role_names=[RoleName.SUPER_ADMIN.value])

    response = client.post(
        f"/api/v1/users/{owner.id}/roles",
        json={"role_names": [RoleName.RECRUITER.value]},
        headers=auth_headers(admin.email, password),
    )

    assert response.status_code == 403


def test_admin_can_still_manage_ordinary_roles(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    recruiter, _ = make_user(role_names=[RoleName.RECRUITER.value])

    response = client.post(
        f"/api/v1/users/{recruiter.id}/roles",
        json={"role_names": [RoleName.HIRING_MANAGER.value]},
        headers=auth_headers(admin.email, password),
    )

    assert response.status_code == 200
    assert response.json()["roles"] == [RoleName.HIRING_MANAGER.value]


def test_super_admin_can_grant_super_admin(client, make_user, auth_headers):
    owner, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    admin, _ = make_user(role_names=[RoleName.ADMIN.value])

    response = client.post(
        f"/api/v1/users/{admin.id}/roles",
        json={"role_names": [RoleName.SUPER_ADMIN.value]},
        headers=auth_headers(owner.email, password),
    )

    assert response.status_code == 200
