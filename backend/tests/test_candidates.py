from app.core.enums import RoleName


def _candidate_payload(**overrides):
    payload = {
        "full_name": "Jamie Rivera",
        "email": "jamie.rivera@example.com",
        "phone": "+1-555-0100",
        "location": "Austin, TX",
        "current_company": "Acme Corp",
        "current_title": "Software Engineer",
        "skills": ["Python", "SQL"],
        "source": "LinkedIn",
        "education": [{"degree": "B.S. Computer Science", "school": "UT Austin", "year": "2019"}],
        "tags": ["Top Talent"],
    }
    payload.update(overrides)
    return payload


def test_recruiter_can_create_candidate(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    response = client.post("/api/v1/candidates", json=_candidate_payload(), headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jamie.rivera@example.com"
    assert body["tags"] == ["Top Talent"]
    assert body["education"][0]["school"] == "UT Austin"
    assert body["duplicate_warnings"] == []


def test_duplicate_email_is_flagged(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    client.post("/api/v1/candidates", json=_candidate_payload(), headers=headers)
    second = client.post(
        "/api/v1/candidates", json=_candidate_payload(full_name="Different Name"), headers=headers
    )

    assert second.status_code == 201
    assert len(second.json()["duplicate_warnings"]) == 1
    assert second.json()["duplicate_warnings"][0]["email"] == "jamie.rivera@example.com"


def test_update_candidate(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = client.post("/api/v1/candidates", json=_candidate_payload(), headers=headers).json()

    response = client.patch(
        f"/api/v1/candidates/{candidate['id']}", json={"status": "Passive", "rating": 4}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Passive"


def test_add_note(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = client.post("/api/v1/candidates", json=_candidate_payload(), headers=headers).json()

    response = client.post(
        f"/api/v1/candidates/{candidate['id']}/notes", json={"body": "Strong communicator"}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["body"] == "Strong communicator"


def test_set_tags_replaces_existing(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = client.post("/api/v1/candidates", json=_candidate_payload(), headers=headers).json()

    response = client.post(
        f"/api/v1/candidates/{candidate['id']}/tags", json={"tags": ["Silver Medalist", "Referral"]}, headers=headers
    )

    assert response.status_code == 200
    assert set(response.json()["tags"]) == {"Silver Medalist", "Referral"}


def test_talent_pool_filter_returns_passive_and_silver_medalist(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    active_candidate = client.post(
        "/api/v1/candidates", json=_candidate_payload(email="active@example.com"), headers=headers
    ).json()
    passive_candidate = client.post(
        "/api/v1/candidates", json=_candidate_payload(email="passive@example.com"), headers=headers
    ).json()
    client.patch(f"/api/v1/candidates/{passive_candidate['id']}", json={"status": "Passive"}, headers=headers)

    response = client.get("/api/v1/candidates", params={"pool": True}, headers=headers)

    ids = {c["id"] for c in response.json()}
    assert passive_candidate["id"] in ids
    assert active_candidate["id"] not in ids
