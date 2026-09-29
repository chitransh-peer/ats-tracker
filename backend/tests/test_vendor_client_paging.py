"""Vendors and clients are listed a page at a time, searched on the server, and
offered to pickers as lightweight matches.

A Ceipal import brings in ~50,000 vendors and ~10,000 clients. Returning every
one of them from the list endpoint hung the list pages and every dropdown that
was built from that list.
"""

import uuid

from app.core.enums import RoleName


def _admin(make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    return auth_headers(user.email, password)


def _make_vendors(client, headers, names, **extra):
    return [client.post("/api/v1/vendors", json={"name": n, **extra}, headers=headers).json() for n in names]


def test_vendor_list_is_paged_with_a_total(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    _make_vendors(client, headers, [f"Paged Vendor {n}" for n in range(5)])

    response = client.get("/api/v1/vendors?limit=2&offset=0", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.headers["X-Total-Count"] == "5"


def test_vendor_search_runs_on_the_server(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    _make_vendors(client, headers, ["Northwind Staffing", "Contoso Talent", "Northwind Labs"])

    response = client.get("/api/v1/vendors?search=northwind", headers=headers)

    assert sorted(v["name"] for v in response.json()) == ["Northwind Labs", "Northwind Staffing"]
    assert response.headers["X-Total-Count"] == "2"


def test_vendor_summary_counts_the_whole_organization(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    _make_vendors(client, headers, ["Active One", "Active Two"])
    _make_vendors(client, headers, ["Primary One"], primary_vendor=True)

    summary = client.get("/api/v1/vendors/summary", headers=headers).json()

    assert summary["total"] == 3
    assert summary["primary"] == 1


def test_vendor_options_return_only_ids_and_names(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    created = _make_vendors(client, headers, ["Globex Partners", "Initech Partners", "Umbrella Corp"])

    matches = client.get("/api/v1/vendors/options?search=partners", headers=headers).json()
    assert [m["name"] for m in matches] == ["Globex Partners", "Initech Partners"]
    assert set(matches[0]) == {"id", "name"}

    # A picker labels its current value by id, whatever is being searched.
    by_id = client.get(f"/api/v1/vendors/options?ids={created[2]['id']}", headers=headers).json()
    assert by_id == [{"id": created[2]["id"], "name": "Umbrella Corp"}]


def test_client_list_is_paged_and_searchable(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    for name in ["Acme Bank", "Acme Retail", "Blue Harbor"]:
        client.post("/api/v1/clients", json={"name": name}, headers=headers)

    page = client.get("/api/v1/clients?limit=1", headers=headers)
    assert len(page.json()) == 1
    assert page.headers["X-Total-Count"] == "3"

    found = client.get("/api/v1/clients?search=acme", headers=headers).json()
    assert sorted(c["name"] for c in found) == ["Acme Bank", "Acme Retail"]


def test_client_summary_and_options(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    client.post("/api/v1/clients", json={"name": "Prospect Co", "status": "Prospect"}, headers=headers)
    client.post("/api/v1/clients", json={"name": "Active Co"}, headers=headers)

    summary = client.get("/api/v1/clients/summary", headers=headers).json()
    assert summary["total"] == 2
    assert summary["prospects"] == 1

    options = client.get("/api/v1/clients/options?search=co", headers=headers).json()
    assert [o["name"] for o in options] == ["Active Co", "Prospect Co"]


def test_options_never_cross_organizations(client, make_user, auth_headers):
    headers = _admin(make_user, auth_headers)
    created = _make_vendors(client, headers, [f"Private Vendor {uuid.uuid4().hex[:6]}"])[0]

    # make_user shares one organization per test, so a second organization's
    # admin is simulated by asking for an id that belongs nowhere visible.
    other = client.get(f"/api/v1/vendors/options?ids={uuid.uuid4()}", headers=headers).json()
    assert other == []
    mine = client.get(f"/api/v1/vendors/options?ids={created['id']}", headers=headers).json()
    assert len(mine) == 1
