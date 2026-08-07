from app.core.enums import RoleName


def _make_client(client, headers, name="Peer Consulting Resources Inc"):
    return client.post("/api/v1/clients", json={"name": name}, headers=headers).json()


def test_create_job_with_full_details(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    account = _make_client(client, headers)

    created = client.post(
        "/api/v1/jobs",
        json={
            "title": "Senior Project Manager - Web & Digital Experiences",
            "client_id": account["id"],
            "end_client": "Metro Digital",
            "business_unit": "Peer Consulting Resources Inc.",
            "facility": "Brooklyn Office",
            "workplace": "Hybrid",
            "employment_type": "Contract",
            "location": "Brooklyn, NY, 11201",
            "city": "Brooklyn",
            "states": ["New York"],
            "country": "United States",
            "postal_code": "11201",
            "openings": 2,
            "pay_min": 98,
            "pay_rate_currency": "USD",
            "pay_rate_unit": "Hourly",
            "pay_rate_type": "C2C",
            "client_bill_rate_min": "115.00",
            "client_bill_rate_unit": "Hourly",
            "client_bill_rate_type": "C2C",
            "respond_by": "Open Until Filled",
            "turnaround_time_value": 3,
            "turnaround_time_unit": "In Days",
            "duration": "12 months",
            "required_hours_per_week": 40,
            "interview_mode": "Video",
            "clearance_required": False,
            "required_documents": ["Resume", "Right to Represent"],
            "work_authorizations": ["US Citizen", "Green Card"],
            "employment_level": "Mid-Senior Level",
            "education": "Bachelors",
            "experience_min_years": 8,
            "experience_max_years": 15,
            "required_skills": ["Project Management", "Agile"],
            "max_allowed_submissions": 5,
            "tax_terms": ["C2C", "W-2"],
            "recruitment_manager_id": str(user.id),
            "primary_recruiter_id": str(user.id),
            "assigned_to_ids": [str(user.id)],
            "comments": "High priority for Q3",
            "notes": [{"body": "Kickoff call done", "note_type": "Job Posting", "action": "Call"}],
            "custom_fields": [{"field_name": "PO Number", "field_value": "PO-8891"}],
            "search_criteria": {
                "boolean_string": '("WEB PROJECT MANAGEMENT") AND ("AZURE DEVOPS")',
                "job_title": "Senior Project Manager",
                "state": "New York",
                "experience_min_years": 8,
                "experience_max_years": 15,
            },
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()

    assert body["req_id"].startswith("REQ-")
    assert body["client_name"] == "Peer Consulting Resources Inc"
    assert body["recruitment_manager_name"] == user.full_name
    assert body["assigned_to_names"] == [user.full_name]
    assert body["created_by_name"] == user.full_name
    assert body["tax_terms"] == ["C2C", "W-2"]
    assert body["states"] == ["New York"]
    assert body["job_age_days"] == 0
    assert body["custom_fields"][0]["field_name"] == "PO Number"
    assert body["search_criteria"]["job_title"] == "Senior Project Manager"

    notes = client.get(f"/api/v1/jobs/{body['id']}/notes", headers=headers)
    assert notes.status_code == 200
    assert notes.json()[0]["action"] == "Call"
    assert notes.json()[0]["author_name"] == user.full_name


def test_job_submissions_reports_stage_progress(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    account = _make_client(client, headers, "Zaass Consulting")

    job = client.post(
        "/api/v1/jobs",
        json={
            "title": "QA Lead",
            "client_id": account["id"],
            "workplace": "Onsite",
            "employment_type": "Contract",
        },
        headers=headers,
    ).json()

    candidate = client.post(
        "/api/v1/candidates",
        json={"full_name": "Zohura Akter", "email": "zohura@example.com", "work_auth": "US Citizen"},
        headers=headers,
    ).json()
    client.post(
        "/api/v1/applications",
        json={"candidate_id": candidate["id"], "job_id": job["id"], "source": "Referral"},
        headers=headers,
    )

    summary = client.get(f"/api/v1/jobs/{job['id']}/submissions", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()

    assert len(body["stages"]) > 0
    assert body["counts"]["All"] == 1
    row = body["submissions"][0]
    assert row["candidate_name"] == "Zohura Akter"
    assert row["work_auth"] == "US Citizen"
    assert row["source"] == "Referral"


def test_save_search_criteria_and_custom_fields(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    job = client.post(
        "/api/v1/jobs",
        json={"title": "CAD QA", "workplace": "Onsite", "employment_type": "Contract"},
        headers=headers,
    ).json()

    saved = client.put(
        f"/api/v1/jobs/{job['id']}/search-criteria",
        json={
            "boolean_string": '("CAD") AND ("QA")',
            "search_mode": "radius",
            "radius_miles": 25,
            "work_authorizations": ["US Citizen"],
            "willing_to_relocate": True,
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["radius_miles"] == 25

    # Saving again updates in place rather than creating a second row.
    resaved = client.put(
        f"/api/v1/jobs/{job['id']}/search-criteria",
        json={"boolean_string": "(CAD)", "radius_miles": 50},
        headers=headers,
    )
    assert resaved.status_code == 200
    assert resaved.json()["id"] == saved.json()["id"]
    assert resaved.json()["radius_miles"] == 50

    field = client.put(
        f"/api/v1/jobs/{job['id']}/custom-fields",
        json={"field_name": "Cost Center", "field_value": "CC-42"},
        headers=headers,
    )
    assert field.status_code == 200
    updated = client.put(
        f"/api/v1/jobs/{job['id']}/custom-fields",
        json={"field_name": "Cost Center", "field_value": "CC-99"},
        headers=headers,
    )
    assert updated.json()["id"] == field.json()["id"]
    assert updated.json()["field_value"] == "CC-99"
