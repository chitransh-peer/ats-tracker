import pytest

from app.core.enums import RoleName
from app.services.roles import service as role_service


@pytest.fixture(autouse=True)
def _restore_roles(db):
    """Roles are global and shared across the test DB, so snapshot every role's
    permissions before each test and restore them afterwards — otherwise a
    grant/revoke here would leak into unrelated permission/scoping tests."""
    snapshot = {
        role.name: [(rp.permission.resource, rp.permission.action) for rp in role.role_permissions]
        for role in role_service.list_roles(db)
    }
    yield
    for role in role_service.list_roles(db):
        if role.name == RoleName.SUPER_ADMIN.value:
            continue
        role_service.set_role_permissions(db, role, snapshot.get(role.name, []))


def _get_role(client, headers, name):
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r for r in roles if r["name"] == name)


def test_super_admin_can_grant_permission_and_it_is_enforced(client, make_user, auth_headers):
    super_admin, sap = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    sa_headers = auth_headers(super_admin.email, sap)

    # Interviewer cannot read jobs by default.
    interviewer, ip = make_user(role_names=[RoleName.INTERVIEWER.value])
    i_headers = auth_headers(interviewer.email, ip)
    assert client.get("/api/v1/jobs", headers=i_headers).status_code == 403

    interviewer_role = _get_role(client, sa_headers, RoleName.INTERVIEWER.value)
    new_perms = interviewer_role["permissions"] + [{"resource": "job", "action": "read"}]

    resp = client.put(
        f"/api/v1/roles/{interviewer_role['id']}/permissions",
        json={"permissions": new_perms},
        headers=sa_headers,
    )
    assert resp.status_code == 200

    # Enforcement is DB-backed, so the interviewer can now read jobs immediately.
    assert client.get("/api/v1/jobs", headers=i_headers).status_code == 200


def test_super_admin_can_revoke_permission(client, make_user, auth_headers):
    super_admin, sap = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    sa_headers = auth_headers(super_admin.email, sap)

    recruiter, rp = make_user(role_names=[RoleName.RECRUITER.value])
    r_headers = auth_headers(recruiter.email, rp)
    assert client.get("/api/v1/jobs", headers=r_headers).status_code == 200

    recruiter_role = _get_role(client, sa_headers, RoleName.RECRUITER.value)
    without_job_read = [p for p in recruiter_role["permissions"] if not (p["resource"] == "job" and p["action"] == "read")]

    resp = client.put(
        f"/api/v1/roles/{recruiter_role['id']}/permissions",
        json={"permissions": without_job_read},
        headers=sa_headers,
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/jobs", headers=r_headers).status_code == 403


def test_non_super_admin_cannot_edit_permissions(client, make_user, auth_headers):
    admin, ap = make_user(role_names=[RoleName.ADMIN.value])
    a_headers = auth_headers(admin.email, ap)
    role = _get_role(client, a_headers, RoleName.INTERVIEWER.value)

    resp = client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permissions": []},
        headers=a_headers,
    )
    assert resp.status_code == 403


def test_super_admin_role_is_immutable(client, make_user, auth_headers):
    super_admin, sap = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    sa_headers = auth_headers(super_admin.email, sap)
    role = _get_role(client, sa_headers, RoleName.SUPER_ADMIN.value)

    resp = client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permissions": [{"resource": "job", "action": "read"}]},
        headers=sa_headers,
    )
    assert resp.status_code == 422
