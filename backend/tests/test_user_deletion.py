"""Permanently deleting a user.

Deactivation already covered the everyday case of someone leaving. This is the
irreversible one, so most of what matters here is what it refuses to do.
"""

import uuid

from sqlalchemy import select

from app.core.enums import RoleName
from app.db.models.audit_log import AuditLog
from app.db.models.user import User


def test_super_admin_can_delete_a_user(client, db, make_user, auth_headers):
    admin, admin_password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    victim, _ = make_user(role_names=[RoleName.RECRUITER.value])
    victim_id = victim.id

    response = client.delete(f"/api/v1/users/{victim_id}", headers=auth_headers(admin.email, admin_password))

    assert response.status_code == 204
    assert db.get(User, victim_id) is None


def test_deleting_frees_the_email_to_be_invited_again(client, db, make_user, auth_headers):
    """Email is unique per organization, so a leftover row would block
    re-inviting someone removed by mistake."""
    admin, admin_password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    headers = auth_headers(admin.email, admin_password)
    victim, _ = make_user(role_names=[RoleName.RECRUITER.value])
    email = victim.email

    assert client.delete(f"/api/v1/users/{victim.id}", headers=headers).status_code == 204

    reinvited = client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "Second Chance", "role_name": RoleName.RECRUITER.value},
        headers=headers,
    )
    assert reinvited.status_code == 201


def test_you_cannot_delete_yourself(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])

    response = client.delete(f"/api/v1/users/{admin.id}", headers=auth_headers(admin.email, password))

    assert response.status_code == 422
    assert "your own account" in response.json()["detail"]


def test_the_last_super_admin_cannot_be_deleted(db, make_user):
    """Otherwise an organization can lose its admin console with no way back in.

    Exercised against the service rather than the endpoint, because the
    endpoint cannot reach it: the caller must be a Super Admin themselves, so
    another one always remains. The guard is there for callers that are not a
    logged-in request -- a maintenance script, a future bulk operation.
    """
    from app.core.exceptions import ValidationAppError
    from app.services.users.service import delete_user

    # Every other Super Admin in this organization is stood down, leaving one.
    only_admin, _ = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    for other in db.scalars(
        select(User).where(User.organization_id == only_admin.organization_id, User.id != only_admin.id)
    ).all():
        other.is_active = False
    db.commit()

    try:
        delete_user(db, only_admin, acting_user_id=uuid.uuid4())
    except ValidationAppError as exc:
        assert "only active Super Admin" in exc.detail
    else:
        raise AssertionError("deleting the last Super Admin should have been refused")


def test_deletion_requires_super_admin(client, make_user, auth_headers):
    """Deactivation is the everyday tool; this one is gated higher."""
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])
    victim, _ = make_user(role_names=[RoleName.RECRUITER.value])

    response = client.delete(f"/api/v1/users/{victim.id}", headers=auth_headers(admin.email, admin_password))
    assert response.status_code == 403


def test_deletion_is_recorded_with_the_identity_it_destroys(client, db, make_user, auth_headers, organization):
    """Their other audit entries lose their author to ON DELETE SET NULL, so
    this one record is what keeps the trace of who was removed."""
    admin, admin_password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    victim, _ = make_user(role_names=[RoleName.RECRUITER.value])
    victim_id, victim_email = victim.id, victim.email

    client.delete(f"/api/v1/users/{victim_id}", headers=auth_headers(admin.email, admin_password))

    entry = db.scalar(
        select(AuditLog)
        .where(AuditLog.action == "user_deleted", AuditLog.resource_id == str(victim_id))
        .order_by(AuditLog.created_at.desc())
    )
    assert entry is not None
    assert entry.actor_user_id == admin.id
    assert entry.metadata_json["email"] == victim_email
    assert RoleName.RECRUITER.value in entry.metadata_json["roles"]


def test_deleting_an_unknown_user_is_a_404(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])

    response = client.delete(f"/api/v1/users/{uuid.uuid4()}", headers=auth_headers(admin.email, password))
    assert response.status_code == 404
