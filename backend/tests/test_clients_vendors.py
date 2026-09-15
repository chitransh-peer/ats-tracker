from app.core.enums import RoleName


def test_admin_can_create_and_list_clients(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    created = client.post("/api/v1/clients", json={"name": "Acme Financial", "industry": "Finance"}, headers=headers)
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


def test_create_client_with_sections_and_snapshot(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    created = client.post(
        "/api/v1/clients",
        json={
            "name": "Steven Douglas",
            "website": "https://www.stevendouglas.com/",
            "industry": "Consulting",
            "category": "Direct",
            "status": "Active",
            "primary_business_unit": "Peer Consulting Resources Inc.",
            "business_unit": "Technology",
            "primary_owner_id": str(user.id),
            "ownership_id": str(user.id),
            "client_lead_id": str(user.id),
            "display_on_job_posting": True,
            "client_visibility": "Organization Level",
            "required_documents": ["Resume", "Right to Represent"],
            "submission_format_fields": ["Candidate name", "Bill rate"],
            "guidelines": "Do not submit candidates already in the client's ATS.",
            "markup_percentage": "42.5",
            "accounts": [{"contact_person": "Dana Kim", "designation": "VP Engineering"}],
            "contacts": [{"name": "Alex Reyes", "email": "alex@example.com"}],
            "notes": [{"body": "Kickoff scheduled", "note_type": "Client"}],
            "assignments": [{"user_id": str(user.id), "assignment_role": "Account Manager"}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()

    assert body["client_code"].startswith("CLI-")
    assert body["created_by_name"] == user.full_name
    assert body["primary_owner_name"] == user.full_name
    assert body["required_documents"] == ["Resume", "Right to Represent"]
    assert len(body["accounts"]) == 1
    assert len(body["contacts"]) == 1
    assert body["assignments"][0]["user_name"] == user.full_name

    snapshot = client.get(f"/api/v1/clients/{body['id']}", headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["accounts"][0]["contact_person"] == "Dana Kim"

    notes = client.get(f"/api/v1/clients/{body['id']}/notes", headers=headers)
    assert notes.status_code == 200
    assert notes.json()[0]["body"] == "Kickoff scheduled"
    assert notes.json()[0]["author_name"] == user.full_name


def test_update_client_records_modifier(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    created = client.post("/api/v1/clients", json={"name": "Orion Retail"}, headers=headers).json()

    updated = client.patch(
        f"/api/v1/clients/{created['id']}",
        json={"status": "Paused", "practice": "Engineering"},
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == "Paused"
    assert updated.json()["practice"] == "Engineering"
    assert updated.json()["updated_by_name"] == user.full_name


def test_client_codes_are_unique_per_organization(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    codes = {
        client.post("/api/v1/clients", json={"name": f"Client {i}"}, headers=headers).json()["client_code"] for i in range(3)
    }

    assert len(codes) == 3


def test_create_vendor_with_sections_and_snapshot(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)

    created = client.post(
        "/api/v1/vendors",
        json={
            "name": "LinkPro Technologies Inc.",
            "website": "https://linkprotech.com",
            "contact_number": "469-598-1886",
            "state": "Texas",
            "country": "United States",
            "city": "Dallas",
            "zip_code": "75201",
            "federal_id": "12-3456789",
            "vendor_type": "Staffing Agency",
            "vendor_classification": "Preferred",
            "payment_terms": "Net 30",
            "primary_business_unit": "Peer Consulting Resources Inc.",
            "business_units": ["Technology", "Healthcare"],
            "vendor_visibility": "Business Unit",
            "primary_owner_id": str(user.id),
            "ownership_id": str(user.id),
            "vendor_lead_id": str(user.id),
            "primary_vendor": True,
            "send_requirement": True,
            "technologies": ["Java", "Cloud / DevOps"],
            "submission_format_fields": ["Candidate name", "Bill rate"],
            "accounts": [{"contact_person": "Christy Vimala", "designation": "Account Manager"}],
            "contacts": [
                {
                    "name": "NICK Powell",
                    "email": "nick@linkprotech.com",
                    "work_phone": "469-598-1886-206",
                    "vms_status": "Not Initiated",
                    "owner_id": str(user.id),
                }
            ],
            "notes": [{"body": "Signed MSA", "action": "Contract", "notified_user_ids": [str(user.id)]}],
            "bank_accounts": [
                {
                    "account_holder_name": "LinkPro Technologies Inc.",
                    "bank_name": "Chase",
                    "account_number": "123456789012",
                    "account_type": "Checking",
                    "is_primary": True,
                }
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()

    assert body["created_by_name"] == user.full_name
    assert body["ownership_name"] == user.full_name
    assert body["business_units"] == ["Technology", "Healthcare"]
    assert body["primary_vendor"] is True
    assert body["accounts"][0]["contact_person"] == "Christy Vimala"
    assert body["contacts"][0]["owner_name"] == user.full_name
    assert body["contacts"][0]["vms_status"] == "Not Initiated"
    assert body["bank_accounts"][0]["bank_name"] == "Chase"

    notes = client.get(f"/api/v1/vendors/{body['id']}/notes", headers=headers)
    assert notes.status_code == 200
    assert notes.json()[0]["action"] == "Contract"
    assert notes.json()[0]["notified_people"] == [user.full_name]


def test_vendor_meetings_and_update(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    vendor = client.post("/api/v1/vendors", json={"name": "TalentBridge"}, headers=headers).json()

    meeting = client.post(
        f"/api/v1/vendors/{vendor['id']}/meetings",
        json={
            "meeting_for": "Quarterly business review",
            "attendee_ids": [str(user.id)],
            "guest_attendees": ["cfo@talentbridge.example"],
            "duration_minutes": 45,
        },
        headers=headers,
    )
    assert meeting.status_code == 201, meeting.text
    assert meeting.json()["attendee_names"] == [user.full_name]
    assert meeting.json()["created_by_name"] == user.full_name

    listed = client.get(f"/api/v1/vendors/{vendor['id']}/meetings", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        f"/api/v1/vendors/{vendor['id']}",
        json={"status": "On Hold", "state": "California"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "On Hold"
    assert updated.json()["state"] == "California"
    assert updated.json()["updated_by_name"] == user.full_name
