"""Bulk actions on applications and the talent bench.

Each batch is committed one item at a time rather than as a single
transaction: one already-rejected application or one already-benched
candidate sitting in a batch of forty must not roll back the other
thirty-nine. These tests pin that partial-success contract.
"""

from app.core.enums import RoleName


def test_bulk_reject_rejects_every_active_application(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job(actor_id=user.id)

    app_ids = []
    for _ in range(3):
        candidate = make_candidate()
        response = client.post(
            "/api/v1/applications",
            json={"candidate_id": str(candidate.id), "job_id": str(job.id)},
            headers=headers,
        )
        app_ids.append(response.json()["id"])

    response = client.post(
        "/api/v1/applications/bulk-reject", json={"application_ids": app_ids}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["succeeded"]) == sorted(app_ids)
    assert body["failed"] == []

    for app_id in app_ids:
        assert client.get(f"/api/v1/applications/{app_id}", headers=headers).json()["status"] == "Rejected"


def test_bulk_reject_reports_partial_failure_without_losing_the_rest(
    client, make_user, make_job, make_candidate, auth_headers
):
    """One already-rejected application in the batch must not stop the
    others from going through."""
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job(actor_id=user.id)

    ids = []
    for _ in range(3):
        candidate = make_candidate()
        response = client.post(
            "/api/v1/applications",
            json={"candidate_id": str(candidate.id), "job_id": str(job.id)},
            headers=headers,
        )
        ids.append(response.json()["id"])

    # Pre-reject the first one so the batch contains a guaranteed failure.
    client.post(f"/api/v1/applications/{ids[0]}/reject", json={}, headers=headers)

    response = client.post("/api/v1/applications/bulk-reject", json={"application_ids": ids}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert ids[0] not in body["succeeded"]
    assert sorted(body["succeeded"]) == sorted(ids[1:])
    assert len(body["failed"]) == 1
    assert body["failed"][0]["application_id"] == ids[0]
    assert "already rejected" in body["failed"][0]["reason"].lower()

    # The two valid ones still went through despite the one failure.
    for app_id in ids[1:]:
        assert client.get(f"/api/v1/applications/{app_id}", headers=headers).json()["status"] == "Rejected"


def test_bulk_hold_only_accepts_active_applications(client, make_user, make_job, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job(actor_id=user.id)
    candidate = make_candidate()
    app_id = client.post(
        "/api/v1/applications",
        json={"candidate_id": str(candidate.id), "job_id": str(job.id)},
        headers=headers,
    ).json()["id"]

    response = client.post("/api/v1/applications/bulk-hold", json={"application_ids": [app_id]}, headers=headers)

    assert response.status_code == 200
    assert app_id in response.json()["succeeded"]
    assert client.get(f"/api/v1/applications/{app_id}", headers=headers).json()["status"] == "On Hold"


def test_bulk_add_to_bench_adds_every_candidate(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate_ids = [str(make_candidate().id) for _ in range(3)]

    response = client.post("/api/v1/talent-bench/bulk", json={"candidate_ids": candidate_ids}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["succeeded"]) == sorted(candidate_ids)
    assert body["failed"] == []

    bench = client.get("/api/v1/talent-bench", headers=headers).json()
    benched_candidate_ids = {row["candidate_id"] for row in bench}
    assert set(candidate_ids) <= benched_candidate_ids


def test_bulk_add_to_bench_reports_already_benched_candidates(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidates = [make_candidate() for _ in range(3)]

    # Bench the first one up front so the batch has a guaranteed failure.
    client.post("/api/v1/talent-bench", json={"candidate_id": str(candidates[0].id)}, headers=headers)

    response = client.post(
        "/api/v1/talent-bench/bulk",
        json={"candidate_ids": [str(c.id) for c in candidates]},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert str(candidates[0].id) not in body["succeeded"]
    assert sorted(body["succeeded"]) == sorted(str(c.id) for c in candidates[1:])
    assert len(body["failed"]) == 1
    assert body["failed"][0]["candidate_id"] == str(candidates[0].id)
    assert "already on the talent bench" in body["failed"][0]["reason"].lower()


def test_bulk_actions_are_still_scoped_by_permission(client, make_user, make_candidate, auth_headers):
    """Bulk endpoints go through the same permission dependency as everything
    else — they don't bypass it just because they take a list."""
    user, password = make_user(role_names=[RoleName.INTERVIEWER.value])
    headers = auth_headers(user.email, password)

    response = client.post(
        "/api/v1/talent-bench/bulk", json={"candidate_ids": [str(make_candidate().id)]}, headers=headers
    )

    assert response.status_code == 403
