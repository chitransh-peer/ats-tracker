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
