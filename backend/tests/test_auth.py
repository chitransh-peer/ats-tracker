from app.core.enums import RoleName
from app.services.auth.service import create_invitation, request_password_reset
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

    reset = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "brand-new-password-123"}
    )
    assert reset.status_code == 204

    login_old = client.post("/api/v1/auth/login", json={"email": user.email, "password": _old_password})
    assert login_old.status_code == 401

    login_new = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "brand-new-password-123"}
    )
    assert login_new.status_code == 200


def test_invitation_accept_creates_active_user(client, db, organization):
    inviter = create_user(
        db,
        organization_id=organization.id,
        email="inviter@example.com",
        full_name="Inviter",
        password="whatever-123",
        role_names=[RoleName.ADMIN.value],
    )

    token = create_invitation(
        db,
        organization_id=organization.id,
        email="invitee@example.com",
        role_name=RoleName.INTERVIEWER.value,
        invited_by=inviter.id,
    )

    response = client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "full_name": "Invitee Person", "password": "invitee-password-123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "invitee@example.com"
    assert body["roles"] == [RoleName.INTERVIEWER.value]

    login = client.post(
        "/api/v1/auth/login", json={"email": "invitee@example.com", "password": "invitee-password-123"}
    )
    assert login.status_code == 200
