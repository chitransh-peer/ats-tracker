"""Interviews, offers, onboarding and hotlists page on the server, carry the
candidate and job names they show, and count their stat cards in SQL; the
pipeline board counts exactly even when it cuts its cards off."""

import pytest

from app.core.enums import RoleName
from app.services.onboarding.service import open_case_for_application
from app.services.pipeline.board import board


@pytest.fixture
def recruiter(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    return user, auth_headers(user.email, password)


def _interview(client, headers, application, when="2030-01-01T10:00:00Z"):
    return client.post(
        "/api/v1/interviews",
        json={"application_id": str(application.id), "round_name": "Screen", "mode": "Video", "scheduled_at": when},
        headers=headers,
    ).json()


def test_application_lists_carry_names_and_search_on_the_server(
    client, recruiter, make_job, make_candidate, make_application
):
    _user, headers = recruiter
    wanted = make_application(candidate=make_candidate(full_name="Zelda Findable"), job=make_job(title="Lighthouse Keeper"))
    make_application(candidate=make_candidate(full_name="Someone Else"), job=make_job(title="Baker"))

    by_name = client.get("/api/v1/applications?page_size=10&search=zelda", headers=headers)
    by_job = client.get("/api/v1/applications?page_size=10&search=lighthouse", headers=headers)

    assert by_name.headers["X-Total-Count"] == "1"
    item = by_name.json()[0]
    assert (item["id"], item["candidate_name"], item["job_title"]) == (
        str(wanted.id),
        "Zelda Findable",
        "Lighthouse Keeper",
    )
    assert [a["id"] for a in by_job.json()] == [str(wanted.id)]


def test_application_options_for_pickers(client, recruiter, make_job, make_candidate, make_application):
    _user, headers = recruiter
    application = make_application(candidate=make_candidate(full_name="Picker Person"), job=make_job(title="Picker Job"))

    matches = client.get("/api/v1/applications/options?search=picker", headers=headers).json()
    by_id = client.get(f"/api/v1/applications/options?ids={application.id}", headers=headers).json()

    expected = [{"id": str(application.id), "candidate_name": "Picker Person", "job_title": "Picker Job"}]
    assert matches == expected
    assert by_id == expected


def test_interviews_are_paged_named_and_summarised(client, recruiter, make_job, make_candidate, make_application):
    _user, headers = recruiter
    job = make_job(title="Interviewed Role")
    applications = [make_application(candidate=make_candidate(full_name=f"Person {i}"), job=job) for i in range(3)]
    for i, application in enumerate(applications):
        _interview(client, headers, application, when=f"2030-01-0{i + 1}T10:00:00Z")
    done = client.get("/api/v1/interviews?limit=1", headers=headers).json()[0]
    client.patch(f"/api/v1/interviews/{done['id']}", json={"status": "Completed"}, headers=headers)

    page = client.get("/api/v1/interviews?limit=2", headers=headers)
    mine = client.get(f"/api/v1/interviews?candidate_id={applications[0].candidate_id}", headers=headers).json()
    summary = client.get("/api/v1/interviews/summary", headers=headers).json()

    assert page.headers["X-Total-Count"] == "3"
    assert [i["candidate_name"] for i in page.json()] == ["Person 2", "Person 1"]  # newest first
    assert page.json()[0]["job_title"] == "Interviewed Role"
    assert [i["application_id"] for i in mine] == [str(applications[0].id)]
    assert summary == {"scheduled": 2, "completed": 1, "awaiting_feedback": 1}


def test_upcoming_interviews_are_soonest_first(client, recruiter, make_job, make_candidate, make_application):
    _user, headers = recruiter
    job = make_job()
    _interview(client, headers, make_application(candidate=make_candidate(), job=job), when="2031-06-01T10:00:00Z")
    soonest = _interview(client, headers, make_application(candidate=make_candidate(), job=job), when="2030-06-01T10:00:00Z")
    _interview(client, headers, make_application(candidate=make_candidate(), job=job), when="2001-01-01T10:00:00Z")

    upcoming = client.get("/api/v1/interviews?upcoming=true", headers=headers).json()

    assert len(upcoming) == 2
    assert upcoming[0]["id"] == soonest["id"]


def test_offers_are_paged_named_and_summarised(client, make_user, auth_headers, make_job, make_candidate, make_application):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, password)
    job = make_job(title="Offered Role")
    for i in range(3):
        application = make_application(candidate=make_candidate(full_name=f"Offeree {i}"), job=job)
        created = client.post(
            "/api/v1/offers", json={"application_id": str(application.id), "base_salary": 100000}, headers=headers
        )
        assert created.status_code == 201, created.text

    page = client.get("/api/v1/offers?limit=2", headers=headers)
    summary = client.get("/api/v1/offers/summary", headers=headers).json()

    assert page.headers["X-Total-Count"] == "3"
    assert page.json()[0]["candidate_name"] == "Offeree 2"
    assert page.json()[0]["job_title"] == "Offered Role"
    assert summary == {"in_progress": 3, "awaiting_approval": 0, "sent": 0, "accepted": 0}


def test_onboarding_is_paged_named_and_summarised(
    client, db, organization, make_user, auth_headers, make_job, make_candidate, make_application
):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, password)
    for i in range(3):
        application = make_application(candidate=make_candidate(full_name=f"Starter {i}"), job=make_job(title="New Role"))
        open_case_for_application(db, organization_id=organization.id, application_id=application.id, actor_id=None)
    db.commit()

    page = client.get("/api/v1/onboarding?limit=2", headers=headers)
    summary = client.get("/api/v1/onboarding/summary", headers=headers).json()

    assert page.headers["X-Total-Count"] == "3"
    assert page.json()[0]["candidate_name"] == "Starter 2"
    assert page.json()[0]["job_title"] == "New Role"
    assert len(page.json()[0]["tasks"]) > 0
    assert summary == {"in_progress": 3, "completed": 0, "cancelled": 0}


def test_hotlists_are_paged_and_searched_with_counts(client, recruiter):
    _user, headers = recruiter
    for name in ("Java bench", "Python bench", "Data bench"):
        client.post("/api/v1/hotlists", json={"name": name}, headers=headers)
    python = next(
        h for h in client.get("/api/v1/hotlists?search=python", headers=headers).json() if h["name"] == "Python bench"
    )
    client.post(
        f"/api/v1/hotlists/{python['id']}/recipients",
        json={"recipients": [{"first_name": "A", "email": "a@x.com"}, {"first_name": "B", "email": "b@x.com"}]},
        headers=headers,
    )

    page = client.get("/api/v1/hotlists?limit=2", headers=headers)
    found = client.get("/api/v1/hotlists?search=python", headers=headers).json()

    assert page.headers["X-Total-Count"] == "3"
    assert len(page.json()) == 2
    assert [(h["name"], h["recipient_count"], h["member_count"]) for h in found] == [("Python bench", 2, 0)]


def test_the_board_counts_every_application_even_past_its_card_limit(
    client, db, organization, recruiter, make_job, make_candidate, make_application
):
    _user, headers = recruiter
    job = make_job(title="Board Role")
    other_job = make_job()
    for _ in range(4):
        make_application(candidate=make_candidate(), job=job)
    make_application(candidate=make_candidate(), job=other_job)

    cut_off = board(db, organization.id, limit=2)
    one_job = client.get(f"/api/v1/pipeline/board?job_id={job.id}", headers=headers).json()

    assert cut_off["total"] == 5
    assert len(cut_off["cards"]) == 2
    assert sum(s["count"] for s in cut_off["stage_counts"]) == 5
    assert one_job["total"] == 4
    assert {c["job_title"] for c in one_job["cards"]} == {"Board Role"}
    assert all(c["candidate_name"] for c in one_job["cards"])


def test_the_board_respects_the_hiring_managers_scope(
    client, make_user, auth_headers, make_job, make_candidate, make_application
):
    hm, password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    headers = auth_headers(hm.email, password)
    make_application(candidate=make_candidate(), job=make_job(hiring_manager_id=hm.id))
    make_application(candidate=make_candidate(), job=make_job())

    assert client.get("/api/v1/pipeline/board", headers=headers).json()["total"] == 1
