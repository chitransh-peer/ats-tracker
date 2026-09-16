from app.core.enums import RoleName


def test_admin_can_read_and_update_organization_settings(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, password)

    read = client.get("/api/v1/settings/organization", headers=headers)
    assert read.status_code == 200
    assert read.json()["settings"]["default_locale"] == "en"

    updated = client.patch(
        "/api/v1/settings/organization", json={"default_locale": "hi", "careers_page_enabled": False}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["settings"]["default_locale"] == "hi"
    assert updated.json()["settings"]["careers_page_enabled"] is False


def test_recruiter_cannot_read_organization_settings(client, make_user, auth_headers):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)

    response = client.get("/api/v1/settings/organization", headers=headers)

    assert response.status_code == 403


def test_executive_cannot_read_organization_settings(client, make_user, auth_headers):
    executive, password = make_user(role_names=[RoleName.EXECUTIVE.value])
    headers = auth_headers(executive.email, password)

    response = client.get("/api/v1/settings/organization", headers=headers)

    assert response.status_code == 403


def test_system_status_is_super_admin_only(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, password)

    # Admin is not Super Admin: this reports deployment-level configuration,
    # so it is gated above the ordinary settings permission.
    assert client.get("/api/v1/settings/system-status", headers=headers).status_code == 403


def test_system_status_reports_configuration_without_leaking_secrets(client, make_user, auth_headers, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(settings, "smtp_username", "postmaster", raising=False)
    monkeypatch.setattr(settings, "smtp_password", "super-secret-value", raising=False)
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-secret-key", raising=False)
    monkeypatch.setattr(settings, "storage_secret_key", "storage-secret-value", raising=False)
    monkeypatch.setattr(settings, "storage_access_key", "storage-access-value", raising=False)

    user, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    headers = auth_headers(user.email, password)

    response = client.get("/api/v1/settings/system-status", headers=headers)
    assert response.status_code == 200
    body = response.json()

    # It says *whether* things are configured...
    assert body["mail_enabled"] is True
    assert body["smtp_host"] == "smtp.example.com"
    assert body["smtp_credentials_set"] is True
    assert body["storage_credentials_set"] is True

    # ...and never what they are. This is the whole point of the endpoint.
    serialized = response.text
    for secret in (
        "super-secret-value",
        "sk-or-secret-key",
        "storage-secret-value",
        "storage-access-value",
    ):
        assert secret not in serialized

    # The database password must not ride along in the connection details.
    assert "database_host" in body
    assert "password" not in serialized.lower()
