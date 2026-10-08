"""Ceipal backup import, end to end through the API, the way the import
screen drives it: stage the tables -> import in chunks -> attach résumés from
ZIP parts -> finish -> undo. And the rule that comes with it: a Ceipal
candidate is never AI-scored.

The rows below follow a real Ceipal "applicants" backup: child tables link
on Applicants.Id (not "Applicant Id"), NULL is `\\N`, users are ids.
"""

import uuid

import pytest
from sqlalchemy import select

from app.api.v1.routes import _documents as documents_route
from app.core.enums import RoleName
from app.core.exceptions import ValidationAppError
from app.db.models.ai import AIEvaluation
from app.db.models.application import Application
from app.db.models.candidate import Candidate, CandidateDocument
from app.db.models.ceipal import CeipalProfile
from app.services.ai.evaluation import create_pending_evaluation
from app.services.ceipal import service as ceipal_service

NULL = "\\N"
PDF = b"%PDF-1.4 resume"
DOCX = b"PK\x03\x04 resume"

APPLICANT_HEADERS = [
    "Id", "Record Type", "Applicant Id", "Bench Id", "First Name", "Last Name", "Middle Name", "Nick Name",
    "Mobile", "Home Phone Number", "Work Phone Number", "Other Phone", "SSN", "Work Authorization", "Skype Id",
    "Source", "City", "Address", "State", "Country", "Postal Code", "Linkedin Url", "Facebook Url", "Twitter Url",
    "Current Company", "Date Of Birth", "Email", "Alternate Email Address", "Expected Pay", "Video Reference",
    "JOb Title", "Experience", "Gender", "Preferred Location", "Status", "Expected Salary", "Primary Skills",
    "Skills", "Created By", "Referred By", "Owners", "Created At", "Modified At",
]  # fmt: skip


def _applicant(ceipal_id, applicant_id, first, last, email, **extra):
    row = {h: "" for h in APPLICANT_HEADERS}
    row.update(
        {
            "Id": ceipal_id,
            "Record Type": "Applicant",
            "Applicant Id": applicant_id,
            "Bench Id": "0",
            "First Name": first,
            "Last Name": last,
            "Email": email,
            "Mobile": "(202) 262-9689",
            "Work Authorization": "US Citizen",
            "Source": "Dice",
            "City": "Austin",
            "State": "Texas",
            "Country": "United States",
            "JOb Title": "Sr. AEM Developer",
            "Experience": "9 Year(s)",
            "Status": "New lead",
            "Skills": "ReactJS,Adobe,Node.Js",
            "Created By": "498455",
            "Owners": "",
            "Created At": "2026-08-02 21:53:29",
            "Modified At": "2026-08-02 21:53:29",
            "SSN": "123-45-6789",
            "Date Of Birth": "1990-01-01",
            "Video Reference": NULL,
        }
    )
    row.update(extra)
    return row


@pytest.fixture
def storage(monkeypatch):
    """Stored files, in memory."""
    files: dict[str, bytes] = {}
    monkeypatch.setattr(ceipal_service, "upload_bytes", lambda key, data, content_type: files.__setitem__(key, data))
    monkeypatch.setattr(ceipal_service, "delete_object", lambda key: files.pop(key, None))
    monkeypatch.setattr(documents_route, "download_bytes", lambda key: files[key])
    return files


@pytest.fixture
def admin(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    return user, auth_headers(user.email, password)


def _stage(client, headers, import_id, kind, rows, *, source=None, first_row=1, header_list=None):
    response = client.post(
        f"/api/v1/imports/ceipal/{import_id}/rows",
        json={
            "kind": kind,
            "source": source or f"{kind}.csv",
            "first_row": first_row,
            "headers": header_list or (list(rows[0]) if rows else []),
            "rows": rows,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _run(client, headers, import_id):
    for _ in range(50):
        response = client.post(f"/api/v1/imports/ceipal/{import_id}/process", headers=headers)
        assert response.status_code == 200, response.text
        job = response.json()
        if job["status"] != "importing":
            return job
    raise AssertionError("import did not finish")


def _send(client, headers, import_id, files):
    response = client.post(
        f"/api/v1/imports/ceipal/{import_id}/documents",
        files=[("files", (name, data, "application/octet-stream")) for name, data in files],
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _backup(client, headers, make_job):
    job = make_job(title="AEM Developer")
    job.req_id = "JPC - 3007"
    response = client.post("/api/v1/imports/ceipal", json={"name": "1791306305_CEIPAL_backup_08_2026"}, headers=headers)
    assert response.status_code == 201, response.text
    imp = response.json()

    _stage(
        client,
        headers,
        imp["id"],
        "applicants",
        [
            _applicant("114453", "114600", "Forrest", "Hardin", "ForrestHardin@Outlook.com", Owners="498455"),
            # Ceipal's own quoting: a nickname with quotes and commas.
            _applicant(
                "115074", "115221", "Yuliya", "Neporent", "yneporent@gmail.com",
                **{"Nick Name": 'Yuliya "Julia" Neporent, CSM, CSPO', "Created By": "-1"},
            ),
            _applicant("115075", "115222", "", "", "noname@example.com"),
        ],
    )  # fmt: skip
    _stage(
        client,
        headers,
        imp["id"],
        "documents",
        [
            {
                "Id": "139372",
                "Applicant ID": "114453",
                "Orignal Document Name": "Forrest Hardin 7-23-26.pdf",
                "Converted Document Name": "6a6ff4991388fForrest-Hardin-7-23-26.pdf",
                "Document Type": "Resume",
                "Default Resume": "1",
            },
            {
                "Id": "140013",
                "Applicant ID": "115074",
                "Orignal Document Name": 'Yuliya "Julia" Neporent, CSM.docx',
                "Converted Document Name": "62272_1787254731Yuliya-Julia-Neporent,-CSM.docx",
                "Document Type": "Resume",
                "Default Resume": "1",
            },
            {
                "Id": "140014",
                "Applicant ID": "115074",
                "Orignal Document Name": "license.pdf",
                "Converted Document Name": "1_license.pdf",
                "Document Type": "Driving License",
                "Default Resume": "0",
            },
            # An applicant from an earlier month, not in this backup.
            {
                "Id": "139371",
                "Applicant ID": "113013",
                "Orignal Document Name": "Knight Resume 2026.docx",
                "Converted Document Name": "6a6dd0d4a761eKnight-Resume-2026.docx",
                "Document Type": "Resume",
                "Default Resume": "0",
            },
        ],
    )
    _stage(
        client,
        headers,
        imp["id"],
        "education",
        [
            {"Id": "52528", "Applicant Id": "114453", "School Name": "The Art Institute of Dallas",
             "Education": "4", "Year Of Completed": "May-2010", "Major Study": "Animation", "Minor Study": ""},
            {"Id": "52530", "Applicant Id": "114453", "School Name": "", "Education": "",
             "Year Of Completed": "", "Major Study": "", "Minor Study": ""},
            {"Id": "1", "Applicant Id": "1", "School Name": "University of North Bengal", "Education": "",
             "Year Of Completed": "January-1993", "Major Study": "Electrical Engineering", "Minor Study": ""},
        ],
    )  # fmt: skip
    _stage(
        client,
        headers,
        imp["id"],
        "submissions",
        [
            {"Id": "57301", "Submission Id": "57463", "Applicant Id": "114453", "Applicant Name": "ForrestHardin",
             "Job Id": "3007", "Job Code": "JPC - 3007", "Record Type": "Pipeline Record", "Profile Status": "Pipeline",
             "Source": "Dice", "Submitted By": "498455", "Submitted On": "2026-08-02 21:53:30", "Pay Rate": "N/A",
             "Bill Rate": "N/A", "Submission Rating": "0", "Resume": "6a6ff4991388fForrest-Hardin-7-23-26.pdf",
             "Date of Available": NULL},
            {"Id": "57302", "Submission Id": "57464", "Applicant Id": "115074", "Applicant Name": "YuliyaNeporent",
             "Job Id": "3999", "Job Code": "JPC - 3999", "Record Type": "Pipeline Record",
             "Profile Status": "Waiting for Evaluation", "Source": "Dice", "Submitted By": NULL,
             "Submitted On": "2026-08-20 15:38:51", "Pay Rate": "N/A", "Bill Rate": "N/A", "Submission Rating": "0",
             "Resume": NULL, "Date of Available": NULL},
        ],
    )  # fmt: skip
    _stage(
        client,
        headers,
        imp["id"],
        "users",
        [{"Id": "498455", "Email": "aarya.marathe@peer-consulting.com"}],
    )
    _stage(client, headers, imp["id"], "degrees", [{"Id": "4", "Name": "Bachelors Degree"}])
    return imp, job


def test_a_backup_is_imported_with_resumes_education_and_submissions(client, db, admin, make_job, storage):
    user, headers = admin
    imp, job = _backup(client, headers, make_job)

    # Sending a batch twice stages it once.
    again = _stage(client, headers, imp["id"], "degrees", [{"Id": "4", "Name": "Bachelors Degree"}])
    assert again["staged"] == 1

    done = _run(client, headers, imp["id"])
    assert done["status"] == "documents"
    assert done["applicants_total"] == 3
    assert done["created_count"] == 2
    assert done["rejected_count"] == 1  # no name
    assert done["documents_expected"] == 3
    assert done["documents_orphaned"] == 1
    assert done["submissions_count"] == 2
    assert done["submissions_linked"] == 1

    forrest = db.scalar(
        select(Candidate).where(
            Candidate.organization_id == user.organization_id,
            Candidate.external_id == "114453",
            Candidate.origin == "ceipal",
        )
    )
    assert forrest.full_name == "Forrest Hardin"
    assert forrest.email == "forresthardin@outlook.com"
    assert forrest.location == "Austin, Texas, United States"
    assert float(forrest.total_experience_years) == 9.0
    assert forrest.skills == ["ReactJS", "Adobe", "Node.Js"]
    assert [(e.degree, e.school, e.year) for e in forrest.education] == [
        ("Bachelors Degree in Animation", "The Art Institute of Dallas", "2010")
    ]

    profile = db.scalar(select(CeipalProfile).where(CeipalProfile.candidate_id == forrest.id))
    # Every column under its Ceipal header, users shown by email, SSN and DOB gone.
    assert profile.fields["JOb Title"] == "Sr. AEM Developer"
    assert profile.fields["Created By"] == "aarya.marathe@peer-consulting.com"
    assert profile.fields["Owners"] == "aarya.marathe@peer-consulting.com"
    assert profile.fields["Video Reference"] == ""
    assert "SSN" not in profile.fields and "Date Of Birth" not in profile.fields

    # The submission to a job we also have became an application -- and no AI review.
    application = db.scalar(select(Application).where(Application.candidate_id == forrest.id))
    assert application.job_id == job.id and application.source == "Ceipal"
    assert db.scalar(select(AIEvaluation).where(AIEvaluation.application_id == application.id)) is None
    assert profile.submissions[0]["job_title"] == "AEM Developer"

    yuliya = db.scalar(
        select(Candidate).where(Candidate.organization_id == user.organization_id, Candidate.external_id == "115074")
    )
    yuliya_profile = db.scalar(select(CeipalProfile).where(CeipalProfile.candidate_id == yuliya.id))
    assert yuliya_profile.fields["Nick Name"] == 'Yuliya "Julia" Neporent, CSM, CSPO'
    assert yuliya_profile.fields["Created By"] == "System"
    assert yuliya_profile.submissions[0]["application_id"] is None  # no such job here

    # Résumés: the ZIP is sent through whole; only listed files attach.
    pending = client.get(f"/api/v1/imports/ceipal/{imp['id']}/documents/pending", headers=headers).json()
    assert sorted(pending["names"]) == [
        "1_license.pdf",
        "62272_1787254731Yuliya-Julia-Neporent,-CSM.docx",
        "6a6ff4991388fForrest-Hardin-7-23-26.pdf",
    ]
    part1 = _send(
        client,
        headers,
        imp["id"],
        [
            ("documents/6a6ff4991388fForrest-Hardin-7-23-26.pdf", PDF),
            ("documents/6a6dd0d4a761eKnight-Resume-2026.docx", DOCX),
            ("documents/stray.pdf", PDF),
            ("documents/1_license.pdf", b"not a pdf"),
        ],
    )
    outcomes = {r["file_name"].split("/")[-1]: r["outcome"] for r in part1["results"]}
    assert outcomes == {
        "6a6ff4991388fForrest-Hardin-7-23-26.pdf": "attached",
        "6a6dd0d4a761eKnight-Resume-2026.docx": "skipped",
        "stray.pdf": "skipped",
        "1_license.pdf": "rejected",
    }
    # The second ZIP part, and a repeat of the first file.
    part2 = _send(
        client,
        headers,
        imp["id"],
        [
            ("62272_1787254731Yuliya-Julia-Neporent,-CSM.docx", DOCX),
            ("6a6ff4991388fForrest-Hardin-7-23-26.pdf", PDF),
        ],
    )
    assert [r["outcome"] for r in part2["results"]] == ["attached", "skipped"]
    assert part2["job"]["documents_attached"] == 2

    db.expire_all()
    profile = db.scalar(select(CeipalProfile).where(CeipalProfile.candidate_id == forrest.id))
    resume = db.get(CandidateDocument, profile.resume_document_id)
    assert resume.file_name == "Forrest Hardin 7-23-26.pdf"
    assert resume.document_type == "resume"
    assert storage[resume.storage_key] == PDF

    report = client.get(f"/api/v1/imports/ceipal/{imp['id']}/report", headers=headers)
    assert report.status_code == 200
    assert "No name." in report.text
    assert "The applicant is not in this backup." in report.text
    assert "The file is not a valid PDF." in report.text

    finished = client.post(f"/api/v1/imports/ceipal/{imp['id']}/finish", headers=headers).json()
    assert finished["status"] == "completed"
    # A part found later can still be added.
    late = _send(client, headers, imp["id"], [("1_license.pdf", PDF)])
    assert late["results"][0]["outcome"] == "skipped"  # it was rejected; the report says why


def test_the_ceipal_view_lists_every_ceipal_column_and_the_resume(client, db, admin, make_job, make_candidate, storage):
    user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    _send(client, headers, imp["id"], [("6a6ff4991388fForrest-Hardin-7-23-26.pdf", PDF)])
    make_candidate(full_name="Not From Ceipal")

    page = client.get("/api/v1/ceipal/candidates", headers=headers).json()
    assert page["total"] == 2
    assert page["columns"][:3] == ["Id", "Record Type", "Applicant Id"]
    assert "SSN" not in page["columns"] and "Date Of Birth" not in page["columns"]
    assert len(page["columns"]) == len(APPLICANT_HEADERS) - 2
    by_name = {r["full_name"]: r for r in page["rows"]}
    forrest = by_name["Forrest Hardin"]
    # Every value sits under the header it had in Ceipal.
    assert forrest["values"]["Email"] == "ForrestHardin@Outlook.com"
    assert forrest["values"]["JOb Title"] == "Sr. AEM Developer"
    assert forrest["values"]["Applicant Id"] == "114600"
    assert forrest["resume"]["file_name"] == "Forrest Hardin 7-23-26.pdf"
    assert by_name["Yuliya Neporent"]["resume"] is None

    download = client.get(
        f"/api/v1/candidates/{forrest['candidate_id']}/documents/{forrest['resume']['document_id']}/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.content == PDF

    searched = client.get("/api/v1/ceipal/candidates?search=yuliya", headers=headers).json()
    assert [r["full_name"] for r in searched["rows"]] == ["Yuliya Neporent"]

    listed = client.get("/api/v1/candidates?origin=ceipal", headers=headers).json()
    assert {c["full_name"] for c in listed} == {"Forrest Hardin", "Yuliya Neporent"}
    assert all(c["origin"] == "ceipal" for c in listed)

    detail = client.get(f"/api/v1/ceipal/candidates/{forrest['candidate_id']}", headers=headers).json()
    assert detail["ceipal_id"] == "114453"
    assert detail["submissions"][0]["job_code"] == "JPC - 3007"


def test_ceipal_candidates_are_never_ai_scored(client, db, admin, make_job, storage):
    user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    forrest = db.scalar(
        select(Candidate).where(
            Candidate.organization_id == user.organization_id,
            Candidate.external_id == "114453",
            Candidate.origin == "ceipal",
        )
    )
    application = db.scalar(select(Application).where(Application.candidate_id == forrest.id))

    response = client.post(f"/api/v1/ai/evaluate-application/{application.id}", headers=headers)
    assert response.status_code == 422
    assert "Ceipal" in response.json()["detail"]

    _send(client, headers, imp["id"], [("6a6ff4991388fForrest-Hardin-7-23-26.pdf", PDF)])
    db.expire_all()
    document = db.scalar(select(CandidateDocument).where(CandidateDocument.candidate_id == forrest.id))
    response = client.post(
        "/api/v1/ai/parse-resume",
        json={"candidate_id": str(forrest.id), "document_id": str(document.id)},
        headers=headers,
    )
    assert response.status_code == 422

    with pytest.raises(ValidationAppError):
        create_pending_evaluation(db, organization_id=forrest.organization_id, application_id=application.id, actor_id=None)
    assert db.scalar(select(AIEvaluation).where(AIEvaluation.application_id == application.id)) is None


def test_a_ceipal_candidate_applying_on_the_careers_page_is_not_scored(client, db, admin, make_job, storage, organization):
    user, headers = admin
    imp, job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    other = make_job(title="Data Engineer")
    other.status = "Active"
    db.commit()

    from fastapi import BackgroundTasks

    from app.services.careers.service import apply_to_job

    background = BackgroundTasks()
    application, candidate = apply_to_job(
        db,
        organization_id=organization.id,
        job_id=other.id,
        full_name="Yuliya Neporent",
        email="yneporent@gmail.com",
        phone=None,
        resume_bytes=None,
        resume_file_name=None,
        resume_content_type=None,
        background_tasks=background,
    )
    assert candidate.origin == "ceipal"
    assert db.scalar(select(AIEvaluation).where(AIEvaluation.application_id == application.id)) is None
    assert background.tasks == []


def test_reimporting_next_months_backup_updates_instead_of_duplicating(client, db, admin, make_job, storage):
    user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])

    second = client.post("/api/v1/imports/ceipal", json={"name": "backup_09_2026"}, headers=headers).json()
    _stage(
        client,
        headers,
        second["id"],
        "applicants",
        [_applicant("114453", "114600", "Forrest", "Hardin", "forresthardin@outlook.com", **{"JOb Title": "Lead"})],
    )
    done = _run(client, headers, second["id"])
    assert done["created_count"] == 0 and done["updated_count"] == 1
    assert done["status"] == "completed"  # no documents in this one

    candidates = db.scalars(
        select(Candidate).where(
            Candidate.organization_id == user.organization_id,
            Candidate.external_id == "114453",
            Candidate.origin == "ceipal",
        )
    ).all()
    assert len(candidates) == 1
    assert candidates[0].current_title == "Lead"
    assert len(candidates[0].education) == 1  # not doubled


def test_an_existing_candidate_with_the_same_email_is_linked_not_duplicated(
    client, db, admin, make_job, make_candidate, storage
):
    user, headers = admin
    existing = make_candidate(full_name="Forrest H.", email="forresthardin@outlook.com", current_company="Acme")
    imp, _job = _backup(client, headers, make_job)
    done = _run(client, headers, imp["id"])
    assert done["created_count"] == 1 and done["updated_count"] == 1

    db.expire_all()
    existing = db.get(Candidate, existing.id)
    assert existing.origin == "ceipal"
    assert existing.full_name == "Forrest H."  # what was here is kept
    assert existing.current_company == "Acme"
    assert existing.current_title == "Sr. AEM Developer"  # blanks are filled

    # Undo leaves them as they were found: no longer a Ceipal candidate.
    _undo(client, headers, imp["id"])
    db.expire_all()
    existing = db.get(Candidate, existing.id)
    assert existing is not None and existing.origin is None
    assert db.scalar(select(CeipalProfile).where(CeipalProfile.candidate_id == existing.id)) is None


def _undo(client, headers, import_id):
    for _ in range(20):
        response = client.post(f"/api/v1/imports/ceipal/{import_id}/undo", headers=headers)
        assert response.status_code == 200, response.text
        if response.json()["status"] == "undone":
            return response.json()
    raise AssertionError("undo did not finish")


def test_undo_removes_the_candidates_and_their_stored_files(client, db, admin, make_job, storage):
    user, headers = admin
    imp, job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    _send(client, headers, imp["id"], [("6a6ff4991388fForrest-Hardin-7-23-26.pdf", PDF)])
    assert len(storage) == 1

    undone = _undo(client, headers, imp["id"])
    assert undone["kept_on_undo"] == 0
    db.expire_all()
    assert (
        db.scalars(
            select(Candidate).where(
                Candidate.organization_id == user.organization_id, Candidate.external_id.in_(["114453", "115074"])
            )
        ).all()
        == []
    )
    assert storage == {}
    assert db.scalar(select(Application).where(Application.job_id == job.id)) is None


def test_staging_rejects_a_file_that_is_not_the_table_it_claims(client, admin):
    user, headers = admin
    imp = client.post("/api/v1/imports/ceipal", json={"name": "x"}, headers=headers).json()
    response = client.post(
        f"/api/v1/imports/ceipal/{imp['id']}/rows",
        json={"kind": "documents", "source": "Applicants.csv", "first_row": 1, "headers": ["Id"], "rows": [{"Id": "1"}]},
        headers=headers,
    )
    assert response.status_code == 422
    # No applicants: nothing to import.
    response = client.post(f"/api/v1/imports/ceipal/{imp['id']}/process", headers=headers)
    assert response.status_code == 422


def test_only_admins_can_import_but_recruiters_see_the_ceipal_view(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    assert client.post("/api/v1/imports/ceipal", json={"name": "x"}, headers=headers).status_code == 403
    assert client.get("/api/v1/ceipal/candidates", headers=headers).status_code == 200


def test_documents_wait_for_the_candidates(client, admin, storage):
    user, headers = admin
    imp = client.post("/api/v1/imports/ceipal", json={"name": "x"}, headers=headers).json()
    response = client.post(
        f"/api/v1/imports/ceipal/{imp['id']}/documents",
        files=[("files", ("a.pdf", PDF, "application/pdf"))],
        headers=headers,
    )
    assert response.status_code == 409


def test_import_ids_are_scoped_to_the_organization(client, admin):
    user, headers = admin
    response = client.get(f"/api/v1/imports/ceipal/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def _forrest_id(client, headers):
    rows = client.get("/api/v1/ceipal/candidates?search=forrest", headers=headers).json()["rows"]
    return rows[0]["candidate_id"]


def test_a_recruiter_can_correct_a_ceipal_record(client, db, admin, make_job, make_user, auth_headers, storage):
    _user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    candidate_id = _forrest_id(client, headers)

    recruiter, password = make_user(role_names=[RoleName.RECRUITER.value])
    recruiter_headers = auth_headers(recruiter.email, password)
    response = client.patch(
        f"/api/v1/ceipal/candidates/{candidate_id}",
        json={"values": {"Mobile": "(512) 555-0100", "JOb Title": "Principal AEM Developer", "City": "Dallas"}},
        headers=recruiter_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["values"]["Mobile"] == "(512) 555-0100"
    assert set(body["edited_columns"]) == {"Mobile", "JOb Title", "City"}

    # The candidate fields drawn from those columns follow the correction.
    candidate = db.get(Candidate, uuid.UUID(candidate_id))
    db.refresh(candidate)
    assert candidate.phone == "(512) 555-0100"
    assert candidate.current_title == "Principal AEM Developer"
    assert candidate.location == "Dallas, Texas, United States"


def test_a_correction_survives_reimporting_the_next_backup(client, db, admin, make_job, storage):
    user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    candidate_id = _forrest_id(client, headers)

    client.patch(
        f"/api/v1/ceipal/candidates/{candidate_id}",
        json={"values": {"Mobile": "(512) 555-0100"}},
        headers=headers,
    )
    # And a fix made through the ordinary candidate edit.
    client.patch(f"/api/v1/candidates/{candidate_id}", json={"current_company": "Acme Corp"}, headers=headers)

    second = client.post("/api/v1/imports/ceipal", json={"name": "backup_09_2026"}, headers=headers).json()
    _stage(
        client,
        headers,
        second["id"],
        "applicants",
        [
            _applicant(
                "114453",
                "114600",
                "Forrest",
                "Hardin",
                "forresthardin@outlook.com",
                **{"JOb Title": "Lead", "Current Company": "Ceipal Co"},
            )
        ],
    )
    _run(client, headers, second["id"])

    candidate = db.get(Candidate, uuid.UUID(candidate_id))
    db.refresh(candidate)
    assert candidate.phone == "(512) 555-0100"  # corrected column kept
    assert candidate.current_company == "Acme Corp"  # edited field kept
    assert candidate.current_title == "Lead"  # untouched field still follows Ceipal
    profile = client.get(f"/api/v1/ceipal/candidates/{candidate_id}", headers=headers).json()
    assert profile["values"]["Mobile"] == "(512) 555-0100"
    assert profile["values"]["JOb Title"] == "Lead"


def test_only_ceipal_columns_can_be_edited(client, admin, make_job, storage):
    _user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    candidate_id = _forrest_id(client, headers)

    response = client.patch(
        f"/api/v1/ceipal/candidates/{candidate_id}", json={"values": {"Not A Column": "x"}}, headers=headers
    )
    assert response.status_code == 422
    identity = client.patch(f"/api/v1/ceipal/candidates/{candidate_id}", json={"values": {"Id": "1"}}, headers=headers)
    assert identity.status_code == 422
    blank_name = client.patch(
        f"/api/v1/ceipal/candidates/{candidate_id}",
        json={"values": {"First Name": "", "Last Name": "", "Nick Name": ""}},
        headers=headers,
    )
    assert blank_name.status_code == 422


def test_editing_a_ceipal_record_needs_candidate_update(client, admin, make_job, make_user, auth_headers, storage):
    _user, headers = admin
    imp, _job = _backup(client, headers, make_job)
    _run(client, headers, imp["id"])
    candidate_id = _forrest_id(client, headers)

    executive, password = make_user(role_names=[RoleName.EXECUTIVE.value])
    response = client.patch(
        f"/api/v1/ceipal/candidates/{candidate_id}",
        json={"values": {"Mobile": "1"}},
        headers=auth_headers(executive.email, password),
    )
    assert response.status_code == 403
