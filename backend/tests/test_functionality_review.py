"""Fixes from the 8 Oct 2026 functionality review: offer pay terms for
contracts and India hires, interview logistics across time zones, global
search, and the recruiter report following job ownership."""

from app.core.enums import JobStatus, RoleName


def _headers(make_user, auth_headers, role=RoleName.RECRUITER):
    user, password = make_user(role_names=[role.value])
    return user, auth_headers(user.email, password)


# ------------------------------------------------------------------ offers


def test_an_hourly_c2c_offer_in_a_contract(client, make_user, make_job, make_candidate, make_application, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    application = make_application(candidate=make_candidate(), job=make_job())

    response = client.post(
        "/api/v1/offers",
        json={
            "application_id": str(application.id),
            "pay_type": "Hourly",
            "hourly_rate": "85.50",
            "currency": "USD",
            "employment_type": "Contract",
            "tax_term": "C2C",
            "contract_duration": "6 months",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    offer = response.json()
    assert offer["pay_type"] == "Hourly"
    assert offer["hourly_rate"] == 85.5
    assert offer["base_salary"] is None
    assert offer["tax_term"] == "C2C"
    assert offer["versions"][0]["hourly_rate"] == 85.5


def test_an_india_payroll_offer_in_inr(client, make_user, make_job, make_candidate, make_application, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    application = make_application(candidate=make_candidate(), job=make_job())

    offer = client.post(
        "/api/v1/offers",
        json={
            "application_id": str(application.id),
            "base_salary": 2500000,
            "currency": "INR",
            "employment_type": "Full-time",
            "tax_term": "India Payroll",
        },
        headers=headers,
    ).json()

    assert offer["pay_type"] == "Salary"
    assert offer["currency"] == "INR"
    assert offer["base_salary"] == 2500000


def test_offer_terms_are_validated(client, make_user, make_job, make_candidate, make_application, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    application_id = str(make_application(candidate=make_candidate(), job=make_job()).id)

    def create(**fields):
        return client.post("/api/v1/offers", json={"application_id": application_id, **fields}, headers=headers)

    assert create(pay_type="Hourly").status_code == 422  # no rate
    assert create().status_code == 422  # salaried without a salary
    assert create(base_salary=100000, currency="EUR").status_code == 422
    assert create(base_salary=100000, tax_term="W-9").status_code == 422
    assert create(base_salary=-5).status_code == 422


def test_switching_an_offer_to_hourly_drops_the_salary(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    _, headers = _headers(make_user, auth_headers)
    application = make_application(candidate=make_candidate(), job=make_job())
    offer = client.post(
        "/api/v1/offers", json={"application_id": str(application.id), "base_salary": 120000}, headers=headers
    ).json()

    response = client.patch(
        f"/api/v1/offers/{offer['id']}",
        json={"pay_type": "Hourly", "hourly_rate": 70, "tax_term": "1099"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["base_salary"] is None and body["hourly_rate"] == 70
    assert [v["pay_type"] for v in body["versions"]] == ["Salary", "Hourly"]


# ------------------------------------------------------------------ interviews


def _schedule(client, headers, application_id, **fields):
    payload = {
        "application_id": str(application_id),
        "round_name": "Technical",
        "mode": "Video",
        "scheduled_at": "2026-10-12T04:00:00Z",
    }
    payload.update(fields)
    return client.post("/api/v1/interviews", json=payload, headers=headers)


def test_an_interview_carries_its_time_zone_interviewer_and_link(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    _, headers = _headers(make_user, auth_headers)
    interviewer, _ = make_user(role_names=[RoleName.INTERVIEWER.value])
    application = make_application(candidate=make_candidate(), job=make_job())

    response = _schedule(
        client,
        headers,
        application.id,
        timezone="Asia/Kolkata",
        duration_minutes=45,
        meeting_link="https://teams.microsoft.com/l/meetup-join/abc",
        panel_user_ids=[str(interviewer.id)],
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["timezone"] == "Asia/Kolkata"
    assert body["duration_minutes"] == 45
    assert body["meeting_link"].startswith("https://teams.microsoft.com")
    # The panel comes back named, and the only interviewer leads.
    assert body["panel_members"] == [
        {"user_id": str(interviewer.id), "full_name": interviewer.full_name, "is_primary": True}
    ]


def test_interview_logistics_are_validated(client, make_user, make_job, make_candidate, make_application, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    application = make_application(candidate=make_candidate(), job=make_job())

    assert _schedule(client, headers, application.id, timezone="Mars/Olympus").status_code == 422
    assert _schedule(client, headers, application.id, meeting_link="javascript:alert(1)").status_code == 422


def test_an_interviewer_from_another_organization_is_refused(
    client, db, make_user, make_job, make_candidate, make_application, auth_headers
):
    from app.db.models.organization import Organization
    from app.services.users.service import create_user

    _, headers = _headers(make_user, auth_headers)
    application = make_application(candidate=make_candidate(), job=make_job())
    other_org = Organization(name="Other", slug=f"other-{application.id.hex[:8]}")
    db.add(other_org)
    db.flush()
    outsider = create_user(
        db,
        organization_id=other_org.id,
        email=f"outsider-{application.id.hex[:8]}@example.com",
        full_name="Outsider",
        password="correct-horse-battery-staple",
        role_names=[RoleName.INTERVIEWER.value],
    )

    response = _schedule(client, headers, application.id, panel_user_ids=[str(outsider.id)])
    assert response.status_code == 422


def test_only_schedulers_change_the_panel(client, make_user, make_job, make_candidate, make_application, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    interviewer, password = make_user(role_names=[RoleName.INTERVIEWER.value])
    colleague, _ = make_user(role_names=[RoleName.INTERVIEWER.value])
    application = make_application(candidate=make_candidate(), job=make_job())
    interview = _schedule(client, headers, application.id, panel_user_ids=[str(interviewer.id)]).json()
    interviewer_headers = auth_headers(interviewer.email, password)

    refused = client.patch(
        f"/api/v1/interviews/{interview['id']}",
        json={"panel_user_ids": [str(interviewer.id), str(colleague.id)]},
        headers=interviewer_headers,
    )
    assert refused.status_code == 403

    # The recruiter who scheduled it can, and can clear the link.
    changed = client.patch(
        f"/api/v1/interviews/{interview['id']}",
        json={"panel_user_ids": [str(colleague.id), str(interviewer.id)], "meeting_link": None},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    panel = {m["user_id"]: m["is_primary"] for m in changed.json()["panel_members"]}
    assert panel == {str(colleague.id): True, str(interviewer.id): False}


# ------------------------------------------------------------------ search


def test_searching_a_req_id_finds_the_job(client, make_user, make_job, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    job = make_job(title="Data Engineer")

    response = client.get(f"/api/v1/search?q={job.req_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [j["id"] for j in body["jobs"]] == [str(job.id)]
    assert body["query"] == job.req_id


def test_search_finds_candidates_and_reports_nothing_found(client, make_user, make_candidate, auth_headers):
    _, headers = _headers(make_user, auth_headers)
    candidate = make_candidate(full_name="Zebediah Quartermaine")

    found = client.get("/api/v1/search?q=quartermaine", headers=headers).json()
    assert [c["id"] for c in found["candidates"]] == [str(candidate.id)]

    nothing = client.get("/api/v1/search?q=REQ-00000000-none", headers=headers).json()
    assert nothing["jobs"] == nothing["candidates"] == nothing["clients"] == nothing["vendors"] == []


def test_search_only_covers_what_the_viewer_can_read(client, make_user, make_job, auth_headers):
    job = make_job(title="Hidden Role")
    _, headers = _headers(make_user, auth_headers, RoleName.INTERVIEWER)

    body = client.get(f"/api/v1/search?q={job.req_id}", headers=headers).json()
    assert body["jobs"] == []


# ------------------------------------------------------------------ recruiter report


def test_the_recruiter_report_counts_primary_recruiters_and_assignees(db, organization, make_user, make_job):
    from app.services.reports import service as report_service

    primary, _ = make_user(role_names=[RoleName.RECRUITER.value])
    assignee, _ = make_user(role_names=[RoleName.RECRUITER.value])
    job = make_job()
    job.primary_recruiter_id = primary.id
    job.assigned_to_ids = [assignee.id, primary.id]
    job.status = JobStatus.ACTIVE.value
    db.commit()

    rows = {r["recruiter_id"]: r for r in report_service.recruiter_performance(db, organization.id)}

    assert rows[primary.id]["open_jobs"] == 1  # once, though named twice
    assert rows[assignee.id]["open_jobs"] == 1


def test_a_recruiters_dashboard_counts_jobs_assigned_to_them(db, organization, make_user, make_job):
    from app.services.reports import service as report_service

    recruiter, _ = make_user(role_names=[RoleName.RECRUITER.value])
    job = make_job()
    job.assigned_to_ids = [recruiter.id]
    job.status = JobStatus.ACTIVE.value
    db.commit()

    assert report_service.recruiter_dashboard(db, organization.id, recruiter.id)["open_jobs"] == 1
