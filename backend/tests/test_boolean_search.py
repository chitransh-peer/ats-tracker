from app.core.enums import RoleName


def _names(client, headers, search):
    response = client.get("/api/v1/candidates", params={"search": search}, headers=headers)
    assert response.status_code == 200, response.text
    return {c["full_name"] for c in response.json()}


def test_boolean_candidate_search(client, make_user, make_candidate, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    make_candidate(full_name="Ann Java", current_title="Java Developer", skills=["Java", "Spring Boot"])
    make_candidate(full_name="Bob Python", current_title="Python Intern", skills=["Python", "Django"])
    make_candidate(full_name="Cy Python", current_title="Python Engineer", skills=["Python", "Flask"])

    assert _names(client, headers, "java AND spring") == {"Ann Java"}
    assert _names(client, headers, "java OR django") == {"Ann Java", "Bob Python"}
    assert _names(client, headers, "python NOT intern") == {"Cy Python"}
    assert _names(client, headers, "python -intern") == {"Cy Python"}
    assert _names(client, headers, 'python AND (django OR flask)') == {"Bob Python", "Cy Python"}
    assert _names(client, headers, '"spring boot"') == {"Ann Java"}
    assert _names(client, headers, "pyth*") == {"Bob Python", "Cy Python"}
    assert _names(client, headers, "ann") == {"Ann Java"}


def test_boolean_search_rejects_unbalanced_parentheses(client, make_user, auth_headers):
    user, password = make_user(role_names=[RoleName.ADMIN.value])
    headers = auth_headers(user.email, password)
    response = client.get("/api/v1/candidates", params={"search": "(java AND"}, headers=headers)
    assert response.status_code in (400, 422)
