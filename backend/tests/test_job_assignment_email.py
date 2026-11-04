from app.core.enums import RoleName


def test_assigning_recruiters_emails_them(client, make_user, auth_headers, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.services.jobs.notifications.dispatch", lambda actor, to, subject, *a, **k: sent.append((to, subject))
    )
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    recruiter, _ = make_user(role_names=[RoleName.RECRUITER.value])
    other, _ = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(admin.email, password)

    created = client.post(
        "/api/v1/jobs",
        json={"title": "NG911 Engineer", "primary_recruiter_id": str(recruiter.id)},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert [to for to, _ in sent] == [recruiter.email]
    assert "NG911 Engineer" in sent[0][1]

    sent.clear()
    job_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"assigned_to_ids": [str(recruiter.id), str(other.id)]},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert [to for to, _ in sent] == [other.email]  # only the newly added recruiter
