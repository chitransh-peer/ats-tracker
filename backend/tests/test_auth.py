import uuid
from datetime import UTC, datetime, timedelta

from app.core.enums import RoleName
from app.services.auth.service import invite_user, request_password_reset
from app.services.users.service import create_user


def test_login_success_returns_token_pair(client, make_user):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])

    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_is_rejected(client, make_user):
    user, _ = make_user(role_names=[RoleName.RECRUITER.value])

    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"})

    assert response.status_code == 401


def test_login_unknown_email_is_rejected(client):
    response = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})

    assert response.status_code == 401


def test_me_returns_current_user_with_roles(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    headers = auth_headers(user.email, password)

    response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["roles"] == [RoleName.HIRING_MANAGER.value]


def test_me_without_token_is_unauthorized(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_refresh_rotates_and_revokes_old_token(client, make_user):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    old_refresh = login.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != old_refresh

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


def test_logout_revokes_refresh_token(client, make_user):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    refresh_token = login.json()["refresh_token"]

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401


def test_reset_password_flow(client, make_user, db):
    user, _old_password = make_user(role_names=[RoleName.RECRUITER.value])

    token = request_password_reset(db, email=user.email)
    assert token is not None

    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "brand-new-password-123"})
    assert reset.status_code == 204

    login_old = client.post("/api/v1/auth/login", json={"email": user.email, "password": _old_password})
    assert login_old.status_code == 401

    login_new = client.post("/api/v1/auth/login", json={"email": user.email, "password": "brand-new-password-123"})
    assert login_new.status_code == 200


def _invite(db, organization, *, role=RoleName.INTERVIEWER.value):
    # Unique per call: the suite runs against the shared dev database, and
    # login resolves an email across every organization, so a fixed address
    # would match a row left behind by an earlier run.
    suffix = uuid.uuid4().hex[:10]
    email = f"invitee-{suffix}@example.com"
    inviter = create_user(
        db,
        organization_id=organization.id,
        email=f"inviter-{suffix}@example.com",
        full_name="Inviter",
        password="whatever-123",
        role_names=[RoleName.ADMIN.value],
    )
    user, temp_password = invite_user(
        db,
        organization_id=organization.id,
        email=email,
        full_name="Invitee Person",
        role_name=role,
        invited_by=inviter.id,
    )
    return user, temp_password


def test_invite_creates_a_user_who_can_log_in_with_the_temporary_password(client, db, organization):
    user, temp_password = _invite(db, organization)

    assert user.must_change_password is True
    assert user.temp_password_expires_at is not None

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": temp_password})
    assert login.status_code == 200


def test_invited_user_is_refused_every_route_but_the_password_change(client, db, organization):
    user, temp_password = _invite(db, organization)
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": temp_password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # The gate is enforced by the API, not merely by the frontend: calling a
    # normal endpoint directly is refused with 403, not served.
    blocked = client.get("/api/v1/users", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Password change required"

    # ...but they can still see who they are, so the UI can explain itself.
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True


def test_changing_the_password_lifts_the_gate(client, db, organization):
    user, temp_password = _invite(db, organization)
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": temp_password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": temp_password, "new_password": "my-own-password-123"},
        headers=headers,
    )
    assert changed.status_code == 200

    # The response carries a new pair, because the old access token still
    # asserts must_change_password and every refresh token was revoked.
    new_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).json()["must_change_password"] is False

    # An interviewer still cannot list users -- that is the ordinary permission
    # matrix. What matters is that the refusal is no longer the password gate.
    blocked = client.get("/api/v1/users", headers=new_headers)
    assert blocked.json()["detail"] != "Password change required"

    # The temporary password is dead; the chosen one works.
    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": temp_password}).status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={"email": user.email, "password": "my-own-password-123"}).status_code == 200
    )


def test_change_password_rejects_a_wrong_current_password(client, db, organization):
    user, temp_password = _invite(db, organization)
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": temp_password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "not-the-temp-password", "new_password": "my-own-password-123"},
        headers=headers,
    )
    assert response.status_code == 401


def test_expired_temporary_password_is_refused_at_login(client, db, organization):
    user, temp_password = _invite(db, organization)
    user.temp_password_expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()

    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": temp_password})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_a_normal_users_password_never_expires(client, db, organization, make_user):
    """temp_password_expires_at is null for a self-chosen password, so the
    expiry branch must not fire for ordinary accounts."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    assert user.temp_password_expires_at is None
    assert user.must_change_password is False

    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": password}).status_code == 200
