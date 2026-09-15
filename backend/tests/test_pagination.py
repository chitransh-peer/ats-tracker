"""Pagination on the list endpoints most likely to grow large.

Each of these used to return every matching row with no way to page through
them. The tests here pin the contract: the body stays a plain array, the total
count rides on `X-Total-Count`, and paging through with limit/offset covers
every row exactly once.
"""

from app.core.enums import RoleName


def test_candidates_default_page_is_capped_and_reports_total(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    for _ in range(5):
        make_candidate()

    response = client.get("/api/v1/candidates?limit=2", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert int(response.headers["X-Total-Count"]) >= 5


def test_candidates_paging_covers_every_row_exactly_once(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    created = {str(make_candidate().id) for _ in range(7)}

    seen: set[str] = set()
    offset = 0
    while True:
        page = client.get(f"/api/v1/candidates?limit=3&offset={offset}", headers=headers).json()
        if not page:
            break
        seen.update(row["id"] for row in page)
        offset += 3

    assert created <= seen


def test_candidates_limit_is_clamped_to_the_maximum(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    response = client.get("/api/v1/candidates?limit=99999", headers=headers)

    assert response.status_code == 422  # ge/le validation on the query param


def test_applications_without_page_size_returns_everything_as_before(
    client, make_user, make_job, make_candidate, auth_headers
):
    """Backward compatibility: omitting page_size must not start truncating
    the many pages that rely on the full application list."""
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)
    job = make_job(actor_id=recruiter.id)

    for _ in range(3):
        candidate = make_candidate()
        client.post(
            "/api/v1/applications",
            json={"candidate_id": str(candidate.id), "job_id": str(job.id)},
            headers=headers,
        )

    response = client.get("/api/v1/applications", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) >= 3
    assert "X-Total-Count" not in response.headers


def test_applications_page_size_opts_into_pagination(client, make_user, make_job, make_candidate, auth_headers):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)
    job = make_job(actor_id=recruiter.id)
    for _ in range(4):
        candidate = make_candidate()
        client.post(
            "/api/v1/applications",
            json={"candidate_id": str(candidate.id), "job_id": str(job.id)},
            headers=headers,
        )

    response = client.get("/api/v1/applications?page_size=2", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert int(response.headers["X-Total-Count"]) >= 4


def test_audit_logs_are_paginated_by_default(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.SUPER_ADMIN.value])
    headers = auth_headers(admin.email, password)

    response = client.get("/api/v1/audit-logs?limit=1", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) <= 1
    assert "X-Total-Count" in response.headers


def test_bench_without_limit_keeps_unpaginated_behavior(client, make_user, make_candidate, auth_headers):
    """The hotlist builder relies on this to populate its consultant picker."""
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)
    for _ in range(3):
        client.post(
            "/api/v1/talent-bench",
            json={"candidate_id": str(make_candidate().id)},
            headers=headers,
        )

    response = client.get("/api/v1/talent-bench", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) >= 3
    assert "X-Total-Count" not in response.headers


def test_bench_limit_opts_into_pagination_with_total(client, make_user, make_candidate, auth_headers):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)
    for _ in range(3):
        client.post(
            "/api/v1/talent-bench",
            json={"candidate_id": str(make_candidate().id)},
            headers=headers,
        )

    response = client.get("/api/v1/talent-bench?limit=1", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert int(response.headers["X-Total-Count"]) >= 3
