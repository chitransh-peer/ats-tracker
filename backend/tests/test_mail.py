import smtplib
from datetime import UTC, datetime

import pytest

from app.core.config import get_settings
from app.core.enums import RoleName
from app.services.mail import messages
from app.services.mail.service import send_email


@pytest.fixture
def mail_settings():
    """Mutates the cached Settings singleton and restores it afterwards."""
    settings = get_settings()
    original = {
        field: getattr(settings, field)
        for field in (
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "smtp_use_tls",
            "app_base_url",
            "expose_password_reset_token",
            "app_env",
        )
    }
    yield settings
    for field, value in original.items():
        setattr(settings, field, value)


def test_send_email_is_a_noop_when_smtp_is_unconfigured(mail_settings):
    mail_settings.smtp_host = ""

    assert send_email(to="someone@example.com", subject="Hi", text_body="Body") is False


def test_send_email_reports_failure_instead_of_raising(mail_settings, monkeypatch):
    """A dead mail server must not take down the request that triggered the send."""
    mail_settings.smtp_host = "smtp.example.com"

    def _explode(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "nope")

    monkeypatch.setattr(smtplib, "SMTP", _explode)

    assert send_email(to="someone@example.com", subject="Hi", text_body="Body") is False


def test_send_email_transmits_when_configured(mail_settings, monkeypatch):
    mail_settings.smtp_host = "smtp.example.com"
    mail_settings.smtp_username = "user"
    mail_settings.smtp_use_tls = True

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["username"] = username

        def send_message(self, message):
            sent["to"] = message["To"]
            sent["subject"] = message["Subject"]

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    assert send_email(to="someone@example.com", subject="Hi", text_body="Body") is True
    assert sent["host"] == "smtp.example.com"
    assert sent["starttls"] is True
    assert sent["username"] == "user"
    assert sent["to"] == "someone@example.com"
    assert sent["subject"] == "Hi"


def test_reset_link_points_at_the_configured_frontend(mail_settings):
    mail_settings.app_base_url = "https://ats.example.com/"

    _subject, text, html = messages.password_reset(token="tok en/+", expires_in_minutes=30)

    # Token must survive URL-encoding so the link still resolves.
    assert "https://ats.example.com/auth/reset-password?token=tok%20en%2F%2B" in text
    assert "https://ats.example.com/auth/reset-password?token=tok%20en%2F%2B" in html
    assert "30 minutes" in text


def test_invitation_carries_the_credential_and_points_at_the_login_page(mail_settings):
    mail_settings.app_base_url = "https://ats.example.com"

    subject, text, html = messages.invitation(
        full_name="Ada Lovelace",
        email="ada@example.com",
        temporary_password="Abcdef-Ghjkmn-Pqrstu",
        organization_name="Peer Consulting",
        role_name="hiring_manager",
        expires_at=datetime(2026, 9, 20, 9, 30, tzinfo=UTC),
    )

    assert "Peer Consulting" in subject
    # There is no acceptance page any more -- the account already exists.
    assert "/auth/invite/accept" not in text
    assert "https://ats.example.com/auth/login" in text
    # Both halves of the credential have to be present, or the mail is useless.
    assert "ada@example.com" in text
    assert "Abcdef-Ghjkmn-Pqrstu" in text
    assert "Abcdef-Ghjkmn-Pqrstu" in html
    assert "hiring manager" in text
    assert "20 Sep 2026" in text


def test_invitation_without_an_expiry_says_so(mail_settings):
    mail_settings.app_base_url = "https://ats.example.com"

    _subject, text, _html = messages.invitation(
        full_name="Ada Lovelace",
        email="ada@example.com",
        temporary_password="Abcdef-Ghjkmn-Pqrstu",
        organization_name="Peer Consulting",
        role_name="recruiter",
        expires_at=None,
    )

    assert "until you sign in and change it" in text


def test_forgot_password_response_is_identical_for_unknown_emails(client, make_user, mail_settings):
    """The endpoint must not reveal which addresses have accounts."""
    # Pin the flag off rather than inheriting whatever this environment sets.
    mail_settings.expose_password_reset_token = False
    user, _ = make_user(role_names=[RoleName.RECRUITER.value])

    known = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json()["detail"] == unknown.json()["detail"]
    assert known.json()["reset_token"] is None
    assert unknown.json()["reset_token"] is None


def test_forgot_password_never_exposes_the_token_in_production(client, make_user, mail_settings):
    """The production guard must win even when the escape hatch is switched on."""
    mail_settings.expose_password_reset_token = True
    mail_settings.app_env = "production"
    user, _ = make_user(role_names=[RoleName.RECRUITER.value])

    response = client.post("/api/v1/auth/forgot-password", json={"email": user.email})

    assert response.status_code == 200
    assert response.json()["reset_token"] is None


def test_email_status_is_readable_by_any_authenticated_user(client, make_user, auth_headers):
    """Recruiters compose outreach, so they need to know whether it will be sent."""
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])

    response = client.get("/api/v1/settings/email-status", headers=auth_headers(recruiter.email, recruiter_password))

    assert response.status_code == 200
    body = response.json()
    assert "enabled" in body
    # Credentials must never appear in the payload.
    assert "smtp_password" not in body
    assert "smtp_username" not in body


def test_email_status_rejects_anonymous_callers(client):
    assert client.get("/api/v1/settings/email-status").status_code == 401
