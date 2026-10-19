"""Ceipal client and vendor exports through the bulk import: the built-in
mappings, owners matched to users, and the rest kept as a note."""

import json

from app.core.enums import RoleName
from tests.test_imports import _check, _csv, _run, _upload

CLIENT_HEADERS = [
    "Client Id",
    "Client Name",
    "Contact Number",
    "Website",
    "Industry",
    "Status",
    "Category",
    "Primary Owner",
    "Business Unit",
    "Display on Job Posting",
    "Created by",
    "Created On",
    "Modified On",
    "Modified By",
    "Primary Business Unit",
]

VENDOR_HEADERS = [
    "Vendor Name",
    "Website",
    "Contact Number",
    "State",
    "Created By",
    "Created On",
    "Country",
    "Ownership",
    "Business Unit",
    "Modified On",
    "Modified By",
]


def test_a_ceipal_client_export_is_imported(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, password)
    rows = [
        [
            "CL-9001",
            "Globex Corp",
            "+1 555 010 2030",
            "globex.example",
            "Manufacturing",
            "Inactive",
            "Direct Client",
            admin.email,
            "Staffing",
            "No",
            "Jane Admin",
            "03/14/2024 10:15 AM",
            "04/01/2024 09:00 AM",
            "John Editor",
            "US Staffing",
        ],
        ["CL-9002", "Initech", "", "", "", "Active", "", "Nobody Here", "", "Yes", "", "", "", "", ""],
    ]
    upload = _upload(client, headers, "clients", "clients.csv", _csv(CLIENT_HEADERS, rows))
    job = upload["job"]
    assert any(p["name"] == "Ceipal clients" for p in upload["presets"])
    # Every Ceipal column is recognised.
    assert all(job["mapping"][h] for h in CLIENT_HEADERS)

    check = _check(client, headers, job["id"], job["mapping"])
    assert check["valid"] == 2
    _run(client, headers, job["id"])

    found = {c["client_code"]: c for c in client.get("/api/v1/clients?search=CL-900", headers=headers).json()}
    globex = found["CL-9001"]
    assert globex["name"] == "Globex Corp"
    assert globex["status"] == "Paused"
    assert globex["category"] == "Direct Client"
    assert globex["primary_owner_id"] == str(admin.id)
    assert globex["business_unit"] == "Staffing"
    assert globex["primary_business_unit"] == "US Staffing"
    assert globex["display_on_job_posting"] is False
    assert globex["created_at"].startswith("2024-03-14")

    notes = client.get(f"/api/v1/clients/{globex['id']}/notes", headers=headers).json()
    assert "Created by: Jane Admin" in notes[0]["body"]
    assert "Modified By: John Editor" in notes[0]["body"]

    initech = found["CL-9002"]
    assert initech["primary_owner_id"] is None
    notes = client.get(f"/api/v1/clients/{initech['id']}/notes", headers=headers).json()
    assert "Primary Owner: Nobody Here" in notes[0]["body"]


def test_a_ceipal_vendor_export_is_imported_from_json_and_reimport_updates(client, make_user, auth_headers):
    admin, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(admin.email, password)
    record = {
        "Vendor Name": "Acme Staffing",
        "Website": "acme.example",
        "Contact Number": "555-0100",
        "State": "TX",
        "Created By": "Jane Admin",
        "Created On": "2024-02-01 08:30:00",
        "Country": "United States",
        "Ownership": admin.email,
        "Business Unit": "Staffing, Consulting",
        "Modified On": "2024-02-02 08:30:00",
        "Modified By": "John Editor",
    }
    upload = _upload(client, headers, "vendors", "vendors.json", json.dumps([record]).encode())
    job = upload["job"]
    assert all(job["mapping"][h] for h in VENDOR_HEADERS)
    _check(client, headers, job["id"], job["mapping"])
    _run(client, headers, job["id"])

    vendor = client.get("/api/v1/vendors?search=Acme Staffing", headers=headers).json()[0]
    assert vendor["state"] == "TX"
    assert vendor["country"] == "United States"
    assert vendor["ownership_id"] == str(admin.id)
    assert vendor["business_units"] == ["Staffing", "Consulting"]
    notes = client.get(f"/api/v1/vendors/{vendor['id']}/notes", headers=headers).json()
    assert "Created By: Jane Admin" in notes[0]["body"]

    # A later export of the same vendor updates it rather than duplicating it.
    upload = _upload(client, headers, "vendors", "vendors.json", json.dumps([{**record, "State": "CA"}]).encode())
    _check(client, headers, upload["job"]["id"], upload["job"]["mapping"], duplicate_mode="update")
    done = _run(client, headers, upload["job"]["id"])
    assert done["updated_count"] == 1
    vendors = client.get("/api/v1/vendors?search=Acme Staffing", headers=headers).json()
    assert len(vendors) == 1
    assert vendors[0]["state"] == "CA"
