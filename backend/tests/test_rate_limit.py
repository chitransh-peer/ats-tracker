"""Rate limits on the unauthenticated endpoints an attacker can hammer without
ever logging in: login, password reset, and the public careers apply form.

The global `_disable_rate_limiting` fixture in conftest turns limiting off for
every other test — these tests turn it back on for their own duration so the
limits themselves get exercised at least once.
"""

import pytest

from app.core.enums import RoleName
from app.core.rate_limit import limiter


@pytest.fixture
def rate_limiting_enabled():
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.enabled = False


def test_login_is_rate_limited_per_ip(client, make_user, rate_limiting_enabled):
    """10/minute — a live attacker can be throttled without touching a
    legitimate user who mistypes a password a couple of times."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])

    statuses = [
        client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong"}).status_code for _ in range(11)
    ]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_forgot_password_is_rate_limited_per_ip(client, make_user, rate_limiting_enabled):
    """5/minute — this is the endpoint that would otherwise let someone spam
    reset emails at an address they don't own."""
    user, _password = make_user(role_names=[RoleName.RECRUITER.value])

    statuses = [client.post("/api/v1/auth/forgot-password", json={"email": user.email}).status_code for _ in range(6)]

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_careers_apply_is_rate_limited_per_ip(client, make_user, auth_headers, organization, rate_limiting_enabled):
    """5/minute — the one endpoint on the whole API that takes a file upload
    from someone who was never asked to log in."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = client.post(
        "/api/v1/jobs",
        json={"title": "Rate Limit Test Role", "workplace": "Remote", "employment_type": "Full-time"},
        headers=headers,
    ).json()
    client.post(f"/api/v1/jobs/{job['id']}/publish", headers=headers)

    def _apply(n: int):
        return client.post(
            f"/api/v1/careers/{organization.slug}/jobs/{job['id']}/apply",
            data={"full_name": f"Applicant {n}", "email": f"applicant{n}@example.com"},
        ).status_code

    statuses = [_apply(n) for n in range(6)]

    assert 429 not in statuses[:5]
    assert statuses[5] == 429
