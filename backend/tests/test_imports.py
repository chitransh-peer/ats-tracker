"""Bulk import, end to end: upload -> check -> import in chunks -> report -> undo,
and export back out.

Exercised through the API, the way the import screen drives it.
"""

import csv
import io
import json

from openpyxl import Workbook

from app.core.enums import RoleName

CEIPAL_HEADERS = [
    "Applicant ID",
    "Applicant Name",
    "Email Address",
    "Mobile Number",
    "City",
    "Source",
    "State",
    "Applicant Status",
    "Job Title",
    "Ownership",
    "Work Authorization",
    "Created By",
    "Created On",
    "Created date",
]


def _admin(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    return auth_headers(user.email, password)


def _tsv(headers, rows) -> bytes:
    """Tab-separated, like a Ceipal export pasted out of Excel."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t")
    writer.writerow(headers)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def _csv(headers, rows) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def _upload(client, headers, entity, file_name, data):
    response = client.post("/api/v1/imports", data={"entity": entity}, files={"file": (file_name, data)}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _check(client, headers, job_id, mapping, duplicate_mode="skip", **extra):
    response = client.post(
        f"/api/v1/imports/{job_id}/check",
        json={"mapping": mapping, "duplicate_mode": duplicate_mode, **extra},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _run(client, headers, job_id):
    """Drive the import to the end, as the import screen does."""
    for _ in range(1000):
        job = client.post(f"/api/v1/imports/{job_id}/process", headers=headers).json()
        if job["status"] == "completed":
            return job
    raise AssertionError("import never completed")


def _ceipal_row(n, *, email=None, phone=None, status="New"):
    return [
        f"CEI-{n}",
        f"Applicant {n}",
        email if email is not None else f"applicant{n}@example.com",
        phone if phone is not None else f"+1 (555) 010-{n:04d}",
        "Austin",
        "LinkedIn",
        "TX",
        status,
        "QA Engineer",
        "Priya Recruiter",
        "H1B",
        "Admin User",
        "03/14/2024",
        "",
    ]


def test_a_ceipal_export_is_recognised_and_imported(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    data = _tsv(CEIPAL_HEADERS, [_ceipal_row(1, status="Active"), _ceipal_row(2), _ceipal_row(3, email="")])

    upload = _upload(client, headers, "candidates", "ceipal.csv", data)
    job = upload["job"]
    # The built-in Ceipal preset matched every column.
    assert job["mapping"]["Applicant ID"] == "external_id"
    assert job["mapping"]["Ownership"] == "note"
    assert job["total_rows"] == 3

    check = _check(client, headers, job["id"], job["mapping"])
    assert check["valid"] == 3
    assert check["invalid"] == 0
    # "New" is not one of this system's statuses: kept, with a warning.
    assert check["with_warnings"] == 2

    done = _run(client, headers, job["id"])
    assert done["created_count"] == 3

    found = client.get("/api/v1/candidates?search=Applicant", headers=headers).json()
    by_name = {c["full_name"]: c for c in found}
    first = by_name["Applicant 1"]
    assert first["location"] == "Austin, TX"
    assert first["current_title"] == "QA Engineer"
    assert first["source"] == "LinkedIn"
    assert first["status"] == "Active"
    assert first["created_at"].startswith("2024-03-14")
    assert "Imported" in first["tags"]
    # No email: imported anyway, and flagged.
    assert by_name["Applicant 3"]["email"] is None
    assert "Missing email" in by_name["Applicant 3"]["tags"]


def test_ownership_and_created_by_become_a_note(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    upload = _upload(client, headers, "candidates", "ceipal.csv", _tsv(CEIPAL_HEADERS, [_ceipal_row(10)]))
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])
    _run(client, headers, upload["job"]["id"])

    candidate = client.get("/api/v1/candidates?search=Applicant 10", headers=headers).json()[0]
    notes = client.get(f"/api/v1/candidates/{candidate['id']}/notes", headers=headers).json()
    assert "Ownership: Priya Recruiter" in notes[0]["body"]
    assert "Created By: Admin User" in notes[0]["body"]


def test_duplicates_are_found_in_the_file_and_in_the_system(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    client.post("/api/v1/candidates", json={"full_name": "Already Here", "email": "applicant1@example.com"}, headers=headers)
    rows = [
        _ceipal_row(1),  # same email as the existing candidate
        _ceipal_row(2),
        _ceipal_row(99, email="applicant2@example.com"),  # same email as row 2
        _ceipal_row(3, email="", phone="555.010.0002"),  # same phone as row 2
    ]
    upload = _upload(client, headers, "candidates", "dupes.csv", _tsv(CEIPAL_HEADERS, rows))

    check = _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])
    assert check["valid"] == 1
    assert check["duplicates"] == 3

    done = _run(client, headers, upload["job"]["id"])
    assert done["created_count"] == 1
    assert done["skipped_count"] == 3


def test_update_mode_fills_in_existing_records_without_blanking_them(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    existing = client.post(
        "/api/v1/candidates",
        json={"full_name": "Old Name", "email": "applicant5@example.com", "current_company": "Keep Me Inc"},
        headers=headers,
    ).json()
    upload = _upload(client, headers, "candidates", "update.csv", _tsv(CEIPAL_HEADERS, [_ceipal_row(5)]))
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"], duplicate_mode="update")

    done = _run(client, headers, upload["job"]["id"])
    assert done["updated_count"] == 1

    updated = client.get(f"/api/v1/candidates/{existing['id']}", headers=headers).json()
    assert updated["full_name"] == "Applicant 5"
    assert updated["current_title"] == "QA Engineer"
    assert updated["current_company"] == "Keep Me Inc"


def test_bad_rows_are_rejected_with_a_reason_and_downloadable(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    rows = [
        ["Good Vendor", "sales@good.example", "12"],
        ["", "orphan@example.com", "3"],
        ["Bad Email Vendor", "not-an-email", "4"],
    ]
    upload = _upload(client, headers, "vendors", "vendors.csv", _csv(["Vendor Name", "Email", "Fax"], rows))
    mapping = upload["job"]["mapping"]
    assert mapping == {"Vendor Name": "name", "Email": "email_id", "Fax": "fax"}

    check = _check(client, headers, upload["job"]["id"], mapping)
    assert check["valid"] == 1
    assert check["invalid"] == 2
    assert {p["row_number"] for p in check["problems"]} == {2, 3}

    done = _run(client, headers, upload["job"]["id"])
    assert done["created_count"] == 1
    assert done["rejected_count"] == 2

    report = client.get(f"/api/v1/imports/{upload['job']['id']}/rejected", headers=headers)
    lines = list(csv.reader(io.StringIO(report.content.decode("utf-8-sig"))))
    assert lines[0] == ["Row", "Problem", "Vendor Name", "Email", "Fax"]
    assert "Vendor name is required" in lines[1][1]
    assert "not a valid email" in lines[2][1]


def test_a_large_import_runs_in_chunks_and_resumes(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    rows = [[f"Chunked Vendor {n:05d}"] for n in range(2500)]
    upload = _upload(client, headers, "vendors", "big.csv", _csv(["Vendor Name"], rows))
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])

    first = client.post(f"/api/v1/imports/{upload['job']['id']}/process", headers=headers).json()
    assert first["status"] == "importing"
    assert first["created_count"] == 1000

    # An interruption here loses nothing: the next call carries on.
    done = _run(client, headers, upload["job"]["id"])
    assert done["created_count"] == 2500
    assert client.get("/api/v1/vendors/summary", headers=headers).json()["total"] == 2500


def test_json_and_excel_files_are_accepted(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)

    payload = json.dumps({"rows": [{"Client": "JSON Client", "Industry": "Banking", "Status": "Prospect"}]})
    upload = _upload(client, headers, "clients", "clients.json", payload.encode())
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])
    assert _run(client, headers, upload["job"]["id"])["created_count"] == 1

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Client Name", "Client ID", "City"])
    sheet.append(["Excel Client", "XL-001", "Pune"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    upload = _upload(client, headers, "clients", "clients.xlsx", buffer.getvalue())
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])
    assert _run(client, headers, upload["job"]["id"])["created_count"] == 1

    names = {c["name"]: c for c in client.get("/api/v1/clients?search=Client", headers=headers).json()}
    assert names["JSON Client"]["status"] == "Prospect"
    assert names["Excel Client"]["client_code"] == "XL-001"
    assert names["JSON Client"]["client_code"].startswith("CLI-")


def test_undo_removes_what_the_import_created_but_keeps_records_in_use(client, make_user, auth_headers, make_job):
    headers = _admin(make_user, auth_headers)
    upload = _upload(client, headers, "candidates", "undo.csv", _tsv(CEIPAL_HEADERS, [_ceipal_row(n) for n in (40, 41, 42)]))
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])
    _run(client, headers, upload["job"]["id"])

    # One of them has since applied to a job, so undo must not delete them.
    candidate = client.get("/api/v1/candidates?search=Applicant 41", headers=headers).json()[0]
    job = make_job()
    client.post("/api/v1/applications", json={"candidate_id": candidate["id"], "job_id": str(job.id)}, headers=headers)

    undone = client.post(f"/api/v1/imports/{upload['job']['id']}/undo", headers=headers).json()
    assert undone["status"] == "undone"
    assert undone["kept_on_undo"] == 1

    remaining = {c["full_name"] for c in client.get("/api/v1/candidates?search=Applicant 4", headers=headers).json()}
    assert remaining == {"Applicant 41"}


def test_jobs_find_their_client_and_bench_finds_its_candidate(client, make_user, auth_headers, make_client):
    headers = _admin(make_user, auth_headers)
    make_client(name="Globex Corporation")
    client.post("/api/v1/candidates", json={"full_name": "Bench Person", "email": "bench@example.com"}, headers=headers)

    jobs = _upload(
        client,
        headers,
        "jobs",
        "jobs.csv",
        _csv(["Title", "Client Name", "Job Type"], [["Data Engineer", "globex corporation", "Contract"]]),
    )
    _check(client, headers, jobs["job"]["id"], jobs["job"]["mapping"])
    assert _run(client, headers, jobs["job"]["id"])["created_count"] == 1

    bench = _upload(
        client,
        headers,
        "bench",
        "bench.csv",
        _csv(["Email", "Marketing Title"], [["bench@example.com", "Senior QA"], ["nobody@example.com", "Ghost"]]),
    )
    check = _check(client, headers, bench["job"]["id"], bench["job"]["mapping"])
    assert check["valid"] == 1
    assert "No candidate with email nobody@example.com" in check["problems"][0]["message"]
    assert _run(client, headers, bench["job"]["id"])["created_count"] == 1


def test_an_export_imports_straight_back_as_duplicates(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    for name in ("Round Trip One", "Round Trip Two"):
        client.post("/api/v1/vendors", json={"name": name, "city": "Denver"}, headers=headers)

    exported = client.get("/api/v1/exports/vendors?format=csv", headers=headers)
    assert exported.status_code == 200
    upload = _upload(client, headers, "vendors", "vendors-export.csv", exported.content)
    check = _check(client, headers, upload["job"]["id"], upload["job"]["mapping"])
    assert check["duplicates"] == 2

    as_json = client.get("/api/v1/exports/vendors?format=json", headers=headers).json()
    assert {v["Vendor name"] for v in as_json} == {"Round Trip One", "Round Trip Two"}


def test_only_admins_can_import_or_export(client, make_user, auth_headers):
    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(recruiter.email, password)

    upload = client.post(
        "/api/v1/imports",
        data={"entity": "vendors"},
        files={"file": ("v.csv", _csv(["Vendor Name"], [["X"]]))},
        headers=headers,
    )
    assert upload.status_code == 403
    assert client.get("/api/v1/exports/candidates", headers=headers).status_code == 403


def test_a_mapping_can_be_saved_and_is_suggested_next_time(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    file = _csv(["Agency", "Mail"], [["Preset Vendor", "p@example.com"]])
    upload = _upload(client, headers, "vendors", "a.csv", file)
    _check(
        client,
        headers,
        upload["job"]["id"],
        {"Agency": "name", "Mail": "email_id"},
        save_preset_as="Agency sheet",
    )

    again = _upload(client, headers, "vendors", "b.csv", file)
    assert again["job"]["mapping"] == {"Agency": "name", "Mail": "email_id"}
    assert any(p["name"] == "Agency sheet" for p in again["presets"])
