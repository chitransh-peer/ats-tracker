from app.core.enums import RoleName


def test_admin_can_create_and_list_clients(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    created = client.post(
        "/api/v1/clients", json={"name": "Acme Financial", "industry": "Finance"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["active_jobs"] == 0

    listed = client.get("/api/v1/clients", headers=headers)
    assert listed.status_code == 200
    assert any(c["name"] == "Acme Financial" for c in listed.json())


def test_recruiter_can_read_but_not_create_client(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    read = client.get("/api/v1/clients", headers=headers)
    write = client.post("/api/v1/clients", json={"name": "Blocked Client"}, headers=headers)

    assert read.status_code == 200
    assert write.status_code == 403


def test_add_client_contact(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    created = client.post("/api/v1/clients", json={"name": "Zephyr Cloud"}, headers=headers).json()

    response = client.post(
        f"/api/v1/clients/{created['id']}/contacts",
        json={"name": "Dana Kim", "email": "dana@zephyr.example", "title": "VP Engineering"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["contacts"][0]["name"] == "Dana Kim"


def test_admin_can_create_and_list_vendors(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    created = client.post(
        "/api/v1/vendors", json={"name": "TalentBridge Partners", "specialization": "Engineering"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["active_submissions"] == 0

    listed = client.get("/api/v1/vendors", headers=headers)
    assert listed.status_code == 200
    assert any(v["name"] == "TalentBridge Partners" for v in listed.json())
