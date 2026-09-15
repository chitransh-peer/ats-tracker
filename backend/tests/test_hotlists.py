"""Hotlist assembly, spreadsheet handling, and dispatch."""

import io

import pytest
from openpyxl import Workbook, load_workbook

from app.core.enums import RoleName


@pytest.fixture
def recruiter(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    return user, auth_headers(user.email, password)


def _bench(client, headers, candidate, **fields):
    return client.post(
        "/api/v1/talent-bench",
        json={"candidate_id": str(candidate.id), **fields},
        headers=headers,
    ).json()


def _hotlist(client, headers, **fields):
    payload = {"name": "Bench hotlist", "subject": "Available consultants", **fields}
    return client.post("/api/v1/hotlists", json=payload, headers=headers).json()


def _recipient_sheet(rows, headers=("First Name", "Last Name", "Email", "Company")):
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_new_hotlist_withholds_candidate_contact_by_default(client, recruiter):
    """Sending consultant emails to a vendor list is how a bench gets poached."""
    _user, headers = recruiter

    hotlist = _hotlist(client, headers)

    assert hotlist["include_candidate_contact"] is False
    assert hotlist["attach_spreadsheet"] is True
    assert hotlist["status"] == "Draft"


def test_members_are_limited_to_bench_profiles_the_sender_can_see(
    client, make_user, make_candidate, auth_headers, recruiter
):
    """A recruiter must not be able to market someone else's consultant just by
    guessing a bench profile id."""
    _user, headers = recruiter
    other, other_password = make_user(role_names=[RoleName.RECRUITER.value])
    other_headers = auth_headers(other.email, other_password)

    mine = _bench(client, headers, make_candidate())
    theirs = _bench(client, other_headers, make_candidate())

    hotlist = _hotlist(client, headers)
    updated = client.put(
        f"/api/v1/hotlists/{hotlist['id']}/members",
        json={"bench_profile_ids": [mine["id"], theirs["id"]]},
        headers=headers,
    ).json()

    member_ids = [m["bench_profile_id"] for m in updated["members"]]
    assert mine["id"] in member_ids
    assert theirs["id"] not in member_ids


def test_recipient_import_accepts_aliases_and_reports_bad_rows(client, recruiter):
    _user, headers = recruiter
    hotlist = _hotlist(client, headers)

    # 'Mail ID' and 'Surname' are aliases; the sheet also has junk to skip.
    data = _recipient_sheet(
        [
            ("Jane", "Doe", "jane@vendor.com", "Vendor One"),
            ("Bad", "Row", "not-an-email", "X"),
            ("Jane", "Again", "JANE@VENDOR.COM", "Vendor One"),
            (None, None, None, None),
        ],
        headers=("First Name", "Surname", "Mail ID", "Vendor"),
    )

    response = client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients/import",
        files={"file": ("recipients.xlsx", data, "application/vnd.ms-excel")},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["added"] == 1
    assert any("not a valid email" in p for p in body["problems"])
    assert any("duplicate" in p for p in body["problems"])


def test_recipient_import_rejects_a_sheet_with_no_email_column(client, recruiter):
    _user, headers = recruiter
    hotlist = _hotlist(client, headers)
    data = _recipient_sheet([("Jane", "555-1234")], headers=("Name", "Phone"))

    response = client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients/import",
        files={"file": ("bad.xlsx", data, "application/vnd.ms-excel")},
        headers=headers,
    )

    assert response.status_code == 422
    assert "email column" in response.json()["detail"].lower()


def test_recipient_import_rejects_a_non_workbook(client, recruiter):
    _user, headers = recruiter
    hotlist = _hotlist(client, headers)

    response = client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients/import",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 422


def test_export_contains_split_names_and_omits_contact_by_default(client, make_candidate, recruiter):
    _user, headers = recruiter
    candidate = make_candidate(full_name="Saravanamuthu Muthukrishnan")
    profile = _bench(client, headers, candidate, desired_rate=70, tax_term="C2C")

    hotlist = _hotlist(client, headers)
    client.put(
        f"/api/v1/hotlists/{hotlist['id']}/members",
        json={"bench_profile_ids": [profile["id"]]},
        headers=headers,
    )

    response = client.get(f"/api/v1/hotlists/{hotlist['id']}/export", headers=headers)

    assert response.status_code == 200
    ws = load_workbook(io.BytesIO(response.content)).active
    header_row = [c.value for c in ws[1]]
    assert header_row[:2] == ["First Name", "Last Name"]
    # Contact withheld unless explicitly enabled.
    assert "Email" not in header_row

    first_row = [c.value for c in ws[2]]
    assert first_row[0] == "Saravanamuthu"
    assert first_row[1] == "Muthukrishnan"


def test_export_includes_email_when_explicitly_enabled(client, make_candidate, recruiter):
    _user, headers = recruiter
    candidate = make_candidate()
    profile = _bench(client, headers, candidate)

    hotlist = _hotlist(client, headers, include_candidate_contact=True)
    client.put(
        f"/api/v1/hotlists/{hotlist['id']}/members",
        json={"bench_profile_ids": [profile["id"]]},
        headers=headers,
    )

    response = client.get(f"/api/v1/hotlists/{hotlist['id']}/export", headers=headers)
    ws = load_workbook(io.BytesIO(response.content)).active

    assert "Email" in [c.value for c in ws[1]]


def test_send_requires_members_recipients_and_a_subject(client, make_candidate, recruiter):
    _user, headers = recruiter
    hotlist = _hotlist(client, headers)

    empty = client.post(f"/api/v1/hotlists/{hotlist['id']}/send", headers=headers)
    assert empty.status_code == 422
    assert "consultant" in empty.json()["detail"]

    profile = _bench(client, headers, make_candidate())
    client.put(
        f"/api/v1/hotlists/{hotlist['id']}/members",
        json={"bench_profile_ids": [profile["id"]]},
        headers=headers,
    )

    no_recipients = client.post(f"/api/v1/hotlists/{hotlist['id']}/send", headers=headers)
    assert no_recipients.status_code == 422
    assert "recipient" in no_recipients.json()["detail"]


def test_send_records_counts_and_skips_unsubscribed(client, make_candidate, recruiter, monkeypatch):
    _user, headers = recruiter
    profile = _bench(client, headers, make_candidate())
    hotlist = _hotlist(client, headers)
    client.put(
        f"/api/v1/hotlists/{hotlist['id']}/members",
        json={"bench_profile_ids": [profile["id"]]},
        headers=headers,
    )

    added = client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients",
        json={
            "recipients": [
                {"first_name": "Jane", "email": "jane@vendor.com"},
                {"first_name": "Raj", "email": "raj@vendor.com"},
            ]
        },
        headers=headers,
    ).json()

    # Unsubscribe one: they must be excluded from the send count.
    target = next(r for r in added["recipients"] if r["email"] == "raj@vendor.com")
    client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients/{target['id']}/unsubscribe",
        headers=headers,
    )

    response = client.post(f"/api/v1/hotlists/{hotlist['id']}/send", headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert body["member_count"] == 1
    assert body["recipient_count"] == 1


def test_recipients_are_deduplicated_within_a_hotlist(client, recruiter):
    _user, headers = recruiter
    hotlist = _hotlist(client, headers)

    client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients",
        json={"recipients": [{"email": "dup@vendor.com"}]},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/hotlists/{hotlist['id']}/recipients",
        json={"recipients": [{"email": "dup@vendor.com"}]},
        headers=headers,
    ).json()

    assert [r["email"] for r in second["recipients"]].count("dup@vendor.com") == 1


def test_recipient_template_is_a_valid_workbook(client, recruiter):
    _user, headers = recruiter

    response = client.get("/api/v1/hotlists/recipient-template", headers=headers)

    assert response.status_code == 200
    ws = load_workbook(io.BytesIO(response.content)).active
    assert [c.value for c in ws[1]] == ["First Name", "Last Name", "Email", "Company"]


def test_hiring_manager_cannot_reach_hotlists(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.HIRING_MANAGER.value])

    response = client.get("/api/v1/hotlists", headers=auth_headers(user.email, password))

    assert response.status_code == 403
