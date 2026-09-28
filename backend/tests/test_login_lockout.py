"""Per-account lockout: the brute-force guard that holds even when guesses
come from many addresses and the per-IP limit never trips."""

from datetime import UTC, datetime

from app.core.enums import RoleName
from app.services.auth.service import MAX_FAILED_LOGINS


def _login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_account_locks_after_repeated_wrong_passwords(client, db, make_user):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])

    for _ in range(MAX_FAILED_LOGINS):
        assert _login(client, user.email, "wrong").status_code == 401

    # Locked now: even the right password is refused until the lock expires.
    response = _login(client, user.email, password)
    assert response.status_code == 401
    assert "Too many failed sign-in attempts" in response.json()["detail"]

    db.refresh(user)
    assert user.locked_until is not None and user.locked_until > datetime.now(UTC)


def test_a_successful_login_resets_the_count(client, db, make_user):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])

    for _ in range(MAX_FAILED_LOGINS - 1):
        _login(client, user.email, "wrong")
    assert _login(client, user.email, password).status_code == 200

    db.refresh(user)
    assert user.failed_login_count == 0
    # So the next mistake starts from one, not from the edge of a lockout.
    assert _login(client, user.email, "wrong").status_code == 401
    assert _login(client, user.email, password).status_code == 200


def test_an_unknown_email_is_refused_like_a_wrong_password(client):
    response = _login(client, "nobody-here@example.com", "whatever-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
