"""
Covers spec section 54 test cases #27 (unauthorized action rejected —
its authentication precondition) plus the audit's required cases 1-3:
successful login, invalid login, inactive user cannot authenticate or
use protected endpoints.
"""


def test_successful_login_returns_token_and_user(client, owner_user):
    response = client.post("/api/auth/login", data={"username": "abbu", "password": "ownerpass123"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "abbu"
    assert body["user"]["role"] == "OWNER"


def test_login_wrong_password_rejected(client, owner_user):
    response = client.post("/api/auth/login", data={"username": "abbu", "password": "wrong-password"})

    assert response.status_code == 401
    # Deliberately generic message — must not reveal whether the username exists.
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_username_rejected(client):
    response = client.post("/api/auth/login", data={"username": "no_such_user", "password": "anything"})

    assert response.status_code == 401


def test_inactive_user_cannot_login(client, inactive_user):
    response = client.post("/api/auth/login", data={"username": "old_employee", "password": "password123"})

    assert response.status_code == 401


def test_deactivating_user_immediately_revokes_existing_token(client, db_session, employee_user):
    """
    is_active is re-checked from the DB on every request, not just at
    login — a token issued before deactivation must stop working on the
    very next request, not linger until it expires.
    """
    headers = client.post(
        "/api/auth/login", data={"username": "employee", "password": "employeepass123"}
    ).json()
    token = headers["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Token works before deactivation.
    ok = client.get("/api/auth/me", headers=auth_header)
    assert ok.status_code == 200

    # Deactivate the account directly (simulating an owner disabling it).
    employee_user.is_active = False
    db_session.add(employee_user)
    db_session.commit()

    blocked = client.get("/api/auth/me", headers=auth_header)
    assert blocked.status_code == 401


def test_protected_endpoint_rejects_missing_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
