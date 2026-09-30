"""Rules for what the job form accepts, enforced on the server so they hold
however a job is created."""

from datetime import date, timedelta

from app.core.enums import RoleName

BASE = {"title": "Rules Check Role", "workplace": "Remote", "employment_type": "Contract"}


def _recruiter(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    return auth_headers(user.email, password)


def _create(client, headers, **fields):
    return client.post("/api/v1/jobs", json={**BASE, **fields}, headers=headers)


def test_negative_pay_and_bill_rates_are_refused(client, make_user, auth_headers):
    headers = _recruiter(make_user, auth_headers)

    assert _create(client, headers, pay_min=-5).status_code == 422
    assert _create(client, headers, client_bill_rate_max="-1").status_code == 422
    assert _create(client, headers, pay_min=0, pay_max=85, client_bill_rate_min="1250.50").status_code == 201


def test_a_minimum_above_its_maximum_is_refused(client, make_user, auth_headers):
    headers = _recruiter(make_user, auth_headers)

    response = _create(client, headers, pay_min=90, pay_max=60)

    assert response.status_code == 422
    assert "Pay rate minimum cannot be more than the maximum" in response.text


def test_required_hours_per_week_must_be_0_to_168(client, make_user, auth_headers):
    headers = _recruiter(make_user, auth_headers)

    assert _create(client, headers, required_hours_per_week=-1).status_code == 422
    assert _create(client, headers, required_hours_per_week=169).status_code == 422
    assert _create(client, headers, required_hours_per_week=40).status_code == 201


def test_respond_by_date_cannot_be_in_the_past(client, make_user, auth_headers):
    headers = _recruiter(make_user, auth_headers)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    past = _create(client, headers, respond_by="Specific Date", respond_by_date=yesterday)
    assert past.status_code == 422
    assert "cannot be in the past" in past.text
    assert _create(client, headers, respond_by="Specific Date", respond_by_date=next_week).status_code == 201


def test_a_job_with_an_old_past_date_can_still_be_edited(client, db, make_user, auth_headers):
    """Jobs saved before this rule may carry a past date; editing something
    else on them must not be blocked by it."""
    from app.db.models.job import Job

    headers = _recruiter(make_user, auth_headers)
    job = _create(client, headers).json()
    db.get(Job, job["id"]).respond_by_date = date.today() - timedelta(days=30)
    db.commit()

    old_date = (date.today() - timedelta(days=30)).isoformat()
    response = client.patch(
        f"/api/v1/jobs/{job['id']}", json={"title": "Renamed", "respond_by_date": old_date}, headers=headers
    )

    assert response.status_code == 200


def test_turnaround_hours_keep_their_minutes(client, make_user, auth_headers):
    headers = _recruiter(make_user, auth_headers)

    created = _create(client, headers, turnaround_time_value=4.5, turnaround_time_unit="In Hours")

    assert created.status_code == 201
    assert created.json()["turnaround_time_value"] == 4.5


def test_a_job_saved_before_these_rules_still_loads(client, db, make_user, auth_headers):
    from app.db.models.job import Job

    headers = _recruiter(make_user, auth_headers)
    job = _create(client, headers).json()
    stored = db.get(Job, job["id"])
    stored.pay_min, stored.pay_max, stored.required_hours_per_week = 100, -20, -3
    db.commit()

    assert client.get(f"/api/v1/jobs/{job['id']}", headers=headers).status_code == 200


def test_recruiters_can_see_names_for_the_job_owner_pickers(client, make_user, auth_headers):
    headers = _recruiter(make_user, auth_headers)
    colleague, _ = make_user(role_names=[RoleName.ADMIN.value])

    options = client.get("/api/v1/users/options", headers=headers)

    assert options.status_code == 200
    assert any(o["id"] == str(colleague.id) for o in options.json())
    # Names only: the full user list, with emails and roles, stays admin-only.
    assert set(options.json()[0]) == {"id", "full_name"}
    assert client.get("/api/v1/users", headers=headers).status_code == 403


def test_numbers_too_large_to_store_are_refused_with_a_message(client, make_user, auth_headers):
    """A pay rate past the 32-bit column used to reach the database and come
    back as a bare 500 ("integer out of range")."""
    headers = _recruiter(make_user, auth_headers)

    too_big = _create(client, headers, pay_max=9_876_543_210)
    assert too_big.status_code == 422
    assert "Pay rate maximum cannot be more than 100,000,000" in too_big.text
    assert _create(client, headers, openings=50_000).status_code == 422
    assert _create(client, headers, experience_min_years=300).status_code == 422
    assert _create(client, headers, pay_max=250_000, openings=3).status_code == 201


def test_a_value_the_database_cannot_hold_is_a_422_not_a_500(client, make_user, auth_headers):
    """The safety net for any field without its own bound: text past a
    column's length is the caller's input, not a server fault."""
    headers = _recruiter(make_user, auth_headers)

    response = _create(client, headers, department="x" * 500)

    assert response.status_code == 422
    assert "too large or too long" in response.text
