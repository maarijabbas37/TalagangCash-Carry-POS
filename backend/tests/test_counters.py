"""
Covers audit-required cases 11-12: the counter lookup endpoint, and
server-side validation of the user/counter relationship.
"""


def test_list_counters_returns_active_counters(client, employee_headers, counter1, counter2):
    response = client.get("/api/counters", headers=employee_headers)

    assert response.status_code == 200
    codes = {c["code"] for c in response.json()}
    assert codes == {"01", "02"}


def test_list_counters_excludes_inactive(client, employee_headers, counter1, inactive_counter):
    response = client.get("/api/counters", headers=employee_headers)

    codes = {c["code"] for c in response.json()}
    assert "01" in codes
    assert "99" not in codes


def test_counters_endpoint_requires_authentication(client):
    response = client.get("/api/counters")
    assert response.status_code == 401


def test_create_user_with_valid_counter_succeeds(client, owner_headers, counter1):
    response = client.post(
        "/api/users",
        json={
            "username": "new_cashier",
            "full_name": "New Cashier",
            "password": "password123",
            "role": "EMPLOYEE",
            "default_counter_id": str(counter1.id),
        },
        headers=owner_headers,
    )
    assert response.status_code == 201
    assert response.json()["username"] == "new_cashier"


def test_create_user_with_nonexistent_counter_rejected(client, owner_headers):
    """
    Phase 1 fix: this must return a friendly 400, not a raw 500 from an
    unhandled FK IntegrityError.
    """
    fake_counter_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        "/api/users",
        json={
            "username": "ghost_cashier",
            "full_name": "Ghost Cashier",
            "password": "password123",
            "role": "EMPLOYEE",
            "default_counter_id": fake_counter_id,
        },
        headers=owner_headers,
    )
    assert response.status_code == 400
    assert "counter" in response.json()["detail"].lower()


def test_create_user_without_counter_is_allowed(client, owner_headers):
    """default_counter_id is nullable by design — a user can float between counters."""
    response = client.post(
        "/api/users",
        json={
            "username": "floating_user",
            "full_name": "Floating User",
            "password": "password123",
            "role": "EMPLOYEE",
        },
        headers=owner_headers,
    )
    assert response.status_code == 201
    assert response.json()["username"] == "floating_user"
