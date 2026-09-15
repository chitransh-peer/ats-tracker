"""Talent Bench, with the emphasis on who can see which consultant.

The visibility rules are the security-relevant part of this feature: a bench is
a commercial asset, and one recruiter's consultants are not automatically
another's to market.
"""

from app.core.enums import RoleName


def _add_to_bench(client, headers, candidate_id, **fields):
    payload = {"candidate_id": str(candidate_id), **fields}
    return client.post("/api/v1/talent-bench", json=payload, headers=headers)


def test_recruiter_can_add_a_candidate_to_the_bench(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    response = _add_to_bench(client, headers, candidate.id, marketing_title="Senior Java Developer", desired_rate=65)

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == candidate.full_name
    assert body["status"] == "Active Bench"
    assert body["bench_age_days"] == 0
    assert body["desired_rate"] == 65.0
    # The creator is always an owner, or they would immediately lose sight of it.
    assert str(user.id) in body["owner_ids"]


def test_bench_codes_are_sequential_per_organization(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)

    first = _add_to_bench(client, headers, make_candidate().id).json()
    second = _add_to_bench(client, headers, make_candidate().id).json()

    assert second["bench_code"] == first["bench_code"] + 1


def test_a_candidate_cannot_be_benched_twice(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    candidate = make_candidate()

    assert _add_to_bench(client, headers, candidate.id).status_code == 201
    duplicate = _add_to_bench(client, headers, candidate.id)

    assert duplicate.status_code == 409
    assert "already on the talent bench" in duplicate.json()["detail"]


def test_removing_and_re_adding_reuses_the_same_profile(client, make_user, make_candidate, auth_headers):
    """A consultant who returns to the bench keeps one history, not two."""
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, admin_password)
    candidate = make_candidate()

    created = _add_to_bench(client, headers, candidate.id).json()
    assert client.delete(f"/api/v1/talent-bench/{created['id']}", headers=headers).status_code == 204

    readded = _add_to_bench(client, headers, candidate.id)

    assert readded.status_code == 201
    assert readded.json()["id"] == created["id"]
    assert readded.json()["bench_code"] == created["bench_code"]


# ------------------------------------------------------------------ visibility


def test_recruiter_cannot_see_another_recruiters_bench_profile(client, make_user, make_candidate, auth_headers):
    owner, owner_password = make_user(role_names=[RoleName.RECRUITER.value])
    other, other_password = make_user(role_names=[RoleName.RECRUITER.value])

    created = _add_to_bench(client, auth_headers(owner.email, owner_password), make_candidate().id).json()

    other_headers = auth_headers(other.email, other_password)

    listed = client.get("/api/v1/talent-bench", headers=other_headers)
    assert listed.status_code == 200
    assert created["id"] not in [row["id"] for row in listed.json()]

    # 404 rather than 403: telling an unauthorised caller that a consultant
    # exists but is hidden still leaks the roster.
    assert client.get(f"/api/v1/talent-bench/{created['id']}", headers=other_headers).status_code == 404


def test_recruiter_sees_a_profile_they_are_named_on(client, make_user, make_candidate, auth_headers):
    owner, owner_password = make_user(role_names=[RoleName.RECRUITER.value])
    colleague, colleague_password = make_user(role_names=[RoleName.RECRUITER.value])

    created = _add_to_bench(
        client,
        auth_headers(owner.email, owner_password),
        make_candidate().id,
        sales_team_member_id=str(colleague.id),
    ).json()

    colleague_headers = auth_headers(colleague.email, colleague_password)

    assert client.get(f"/api/v1/talent-bench/{created['id']}", headers=colleague_headers).status_code == 200
    assert created["id"] in [row["id"] for row in client.get("/api/v1/talent-bench", headers=colleague_headers).json()]


def test_adding_an_owner_grants_visibility(client, make_user, make_candidate, auth_headers):
    owner, owner_password = make_user(role_names=[RoleName.RECRUITER.value])
    colleague, colleague_password = make_user(role_names=[RoleName.RECRUITER.value])
    owner_headers = auth_headers(owner.email, owner_password)
    colleague_headers = auth_headers(colleague.email, colleague_password)

    created = _add_to_bench(client, owner_headers, make_candidate().id).json()
    assert client.get(f"/api/v1/talent-bench/{created['id']}", headers=colleague_headers).status_code == 404

    client.patch(
        f"/api/v1/talent-bench/{created['id']}",
        json={"owner_ids": [str(owner.id), str(colleague.id)]},
        headers=owner_headers,
    )

    assert client.get(f"/api/v1/talent-bench/{created['id']}", headers=colleague_headers).status_code == 200


def test_admin_sees_the_whole_bench(client, make_user, make_candidate, auth_headers):
    recruiter, recruiter_password = make_user(role_names=[RoleName.RECRUITER.value])
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])

    created = _add_to_bench(client, auth_headers(recruiter.email, recruiter_password), make_candidate().id).json()

    listed = client.get("/api/v1/talent-bench", headers=auth_headers(admin.email, admin_password))

    assert created["id"] in [row["id"] for row in listed.json()]


def test_hiring_manager_sees_only_actively_marketed_consultants(client, make_user, make_candidate, auth_headers):
    """`Do Not Market` usually signals a commercial or personal reason that is
    not a hiring manager's business."""
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])
    manager, manager_password = make_user(role_names=[RoleName.HIRING_MANAGER.value])
    admin_headers = auth_headers(admin.email, admin_password)

    marketed = _add_to_bench(client, admin_headers, make_candidate().id).json()
    withheld = _add_to_bench(client, admin_headers, make_candidate().id, status="Do Not Market").json()

    visible = [
        row["id"] for row in client.get("/api/v1/talent-bench", headers=auth_headers(manager.email, manager_password)).json()
    ]

    assert marketed["id"] in visible
    assert withheld["id"] not in visible


def test_interviewer_has_no_bench_access_at_all(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.INTERVIEWER.value])

    response = client.get("/api/v1/talent-bench", headers=auth_headers(user.email, password))

    assert response.status_code == 403


def test_hiring_manager_cannot_modify_the_bench(client, make_user, make_candidate, auth_headers):
    admin, admin_password = make_user(role_names=[RoleName.ADMIN.value])
    manager, manager_password = make_user(role_names=[RoleName.HIRING_MANAGER.value])

    created = _add_to_bench(client, auth_headers(admin.email, admin_password), make_candidate().id).json()

    response = client.patch(
        f"/api/v1/talent-bench/{created['id']}",
        json={"marketing_title": "Changed"},
        headers=auth_headers(manager.email, manager_password),
    )

    assert response.status_code == 403


def test_summary_counts_respect_visibility(client, make_user, make_candidate, auth_headers):
    owner, owner_password = make_user(role_names=[RoleName.RECRUITER.value])
    other, other_password = make_user(role_names=[RoleName.RECRUITER.value])

    _add_to_bench(client, auth_headers(owner.email, owner_password), make_candidate().id)

    summary = client.get("/api/v1/talent-bench/summary", headers=auth_headers(other.email, other_password)).json()

    # The other recruiter owns nothing, so their dashboard must not count it.
    assert summary["total"] == 0
