"""The jobs list is paged and costs the same number of queries however many
jobs are on the page."""

from contextlib import contextmanager

from sqlalchemy import event

from app.core.enums import JobStatus, RoleName
from app.db.session import engine


@contextmanager
def _count_queries():
    statements: list[str] = []

    def _record(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", _record)


def _recruiter_headers(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    return user, auth_headers(user.email, password)


def test_the_list_makes_the_same_number_of_queries_for_3_or_30_jobs(
    client, make_user, make_job, make_candidate, make_application, make_client, auth_headers
):
    user, headers = _recruiter_headers(make_user, auth_headers)
    customer = make_client()

    def _add_jobs(count):
        for _ in range(count):
            job = make_job(
                client_id=customer.id, recruitment_manager_id=user.id, assigned_to_ids=[user.id], actor_id=user.id
            )
            make_application(candidate=make_candidate(), job=job)

    _add_jobs(3)
    with _count_queries() as few:
        assert len(client.get("/api/v1/jobs", headers=headers).json()) == 3
    _add_jobs(27)
    with _count_queries() as many:
        assert len(client.get("/api/v1/jobs", headers=headers).json()) == 30

    assert len(many) == len(few)


def test_jobs_are_paged_with_a_total(client, make_user, make_job, auth_headers):
    _user, headers = _recruiter_headers(make_user, auth_headers)
    for i in range(5):
        make_job(title=f"Paged Role {i}")

    response = client.get("/api/v1/jobs?limit=2&offset=2", headers=headers)

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "5"
    assert [j["title"] for j in response.json()] == ["Paged Role 2", "Paged Role 1"]


def test_job_counts_are_right_on_the_list(client, make_user, make_job, make_candidate, make_application, auth_headers):
    _user, headers = _recruiter_headers(make_user, auth_headers)
    busy = make_job(title="Busy Role")
    make_job(title="Quiet Role")
    for _ in range(3):
        make_application(candidate=make_candidate(), job=busy)

    jobs = {j["title"]: j for j in client.get("/api/v1/jobs", headers=headers).json()}

    assert jobs["Busy Role"]["applications_count"] == 3
    assert jobs["Quiet Role"]["applications_count"] == 0


def test_search_matches_title_job_code_and_client(client, make_user, make_job, make_client, auth_headers):
    _user, headers = _recruiter_headers(make_user, auth_headers)
    acme = make_client(name="Acme Searchable Corp")
    by_title = make_job(title="Quantum Plumber")
    by_client = make_job(title="Something Else", client_id=acme.id)
    make_job(title="Unrelated")

    def found(term):
        return {j["id"] for j in client.get(f"/api/v1/jobs?search={term}", headers=headers).json()}

    assert found("quantum") == {str(by_title.id)}
    assert found("acme searchable") == {str(by_client.id)}
    assert found(by_title.req_id) == {str(by_title.id)}


def test_summary_counts_by_status(client, db, make_user, make_job, auth_headers):
    _user, headers = _recruiter_headers(make_user, auth_headers)
    for status in (JobStatus.ACTIVE, JobStatus.ACTIVE, JobStatus.DRAFT, JobStatus.ON_HOLD, JobStatus.CLOSED):
        make_job().status = status.value
    db.commit()

    summary = client.get("/api/v1/jobs/summary", headers=headers).json()

    assert summary == {"total": 5, "active": 2, "draft": 1, "closed_or_on_hold": 2}


def test_options_search_and_look_up_by_id(client, db, make_user, make_job, auth_headers):
    _user, headers = _recruiter_headers(make_user, auth_headers)
    open_job = make_job(title="Picker Target")
    open_job.status = JobStatus.ACTIVE.value
    make_job(title="Picker Draft")
    db.commit()

    matches = client.get("/api/v1/jobs/options?search=picker", headers=headers).json()
    only_open = client.get("/api/v1/jobs/options?search=picker&status=Active", headers=headers).json()
    by_id = client.get(f"/api/v1/jobs/options?ids={open_job.id}", headers=headers).json()

    assert {m["title"] for m in matches} == {"Picker Target", "Picker Draft"}
    assert [m["title"] for m in only_open] == ["Picker Target"]
    assert by_id == [{"id": str(open_job.id), "title": "Picker Target", "req_id": open_job.req_id, "status": "Active"}]


def test_options_respect_the_hiring_managers_scope(client, make_user, make_job, auth_headers):
    hm, password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    headers = auth_headers(hm.email, password)
    mine = make_job(title="Scoped Mine", hiring_manager_id=hm.id)
    make_job(title="Scoped Theirs")

    matches = client.get("/api/v1/jobs/options?search=scoped", headers=headers).json()

    assert [m["id"] for m in matches] == [str(mine.id)]
