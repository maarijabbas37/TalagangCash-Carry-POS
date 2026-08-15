"""
Covers audit-required cases 4-5: owner-only endpoint access granted for
Owner, denied for Employee. Uses /api/users (list users) as the
representative owner-only endpoint since it has no side effects to clean
up, per spec section 4 ("Manage users — Owner only").
"""


def test_owner_can_access_owner_only_endpoint(client, owner_headers):
    response = client.get("/api/users", headers=owner_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_employee_denied_owner_only_endpoint(client, employee_headers):
    response = client.get("/api/users", headers=employee_headers)
    assert response.status_code == 403
    assert "owner" in response.json()["detail"].lower()


def test_owner_only_endpoint_denied_without_auth(client):
    response = client.get("/api/users")
    assert response.status_code == 401
