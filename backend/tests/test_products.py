"""
Covers audit-required cases 6-10: product creation, duplicate
barcode/internal-code rejection, price history correctness, and the
Phase 1 fix — product edit is now Owner-only, and both edits and price
changes must be auditable.
"""


def _create_product(client, headers, **overrides):
    payload = {
        "name": "Surf Excel 90g",
        "barcode": "123456789",
        "unit": "pcs",
        "sale_price": "110.00",
    }
    payload.update(overrides)
    return client.post("/api/products", json=payload, headers=headers)


def test_employee_can_create_product(client, employee_headers):
    response = _create_product(client, employee_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Surf Excel 90g"
    assert body["sale_price"] == "110.00"
    assert body["is_active"] is True


def test_duplicate_barcode_rejected(client, employee_headers):
    first = _create_product(client, employee_headers, internal_code="301")
    assert first.status_code == 201

    duplicate = _create_product(
        client, employee_headers, name="Different Product", internal_code="302"
    )
    assert duplicate.status_code == 409
    assert "barcode" in duplicate.json()["detail"].lower()


def test_duplicate_internal_code_rejected(client, employee_headers):
    first = _create_product(client, employee_headers, barcode="111", internal_code="301")
    assert first.status_code == 201

    duplicate = _create_product(
        client, employee_headers, name="Different Product", barcode="222", internal_code="301"
    )
    assert duplicate.status_code == 409
    assert "internal code" in duplicate.json()["detail"].lower()


def test_price_change_creates_price_history_entry(client, owner_headers):
    created = _create_product(client, owner_headers).json()
    product_id = created["id"]

    response = client.put(
        f"/api/products/{product_id}/price", json={"new_price": "115.00"}, headers=owner_headers
    )
    assert response.status_code == 200
    assert response.json()["sale_price"] == "115.00"

    history = client.get(f"/api/products/{product_id}/price-history", headers=owner_headers)
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 1
    assert rows[0]["old_price"] == "110.00"
    assert rows[0]["new_price"] == "115.00"


def test_employee_cannot_change_price(client, employee_headers):
    created = _create_product(client, employee_headers).json()
    response = client.put(
        f"/api/products/{created['id']}/price", json={"new_price": "999.00"}, headers=employee_headers
    )
    assert response.status_code == 403


# --- Phase 1 fix: product edit authorization ---

def test_employee_cannot_edit_product(client, employee_headers):
    created = _create_product(client, employee_headers).json()

    response = client.put(
        f"/api/products/{created['id']}", json={"name": "Renamed"}, headers=employee_headers
    )
    assert response.status_code == 403


def test_employee_cannot_deactivate_product(client, employee_headers):
    """
    The specific gap flagged in the Phase 1 audit: an employee must not
    be able to flip is_active on an existing product.
    """
    created = _create_product(client, employee_headers).json()

    response = client.put(
        f"/api/products/{created['id']}", json={"is_active": False}, headers=employee_headers
    )
    assert response.status_code == 403

    # Confirm it's genuinely unchanged, not just that the response was blocked.
    unchanged = client.get(f"/api/products/{created['id']}", headers=employee_headers)
    assert unchanged.json()["is_active"] is True


def test_owner_can_edit_product_and_it_is_audited(client, owner_headers):
    created = _create_product(client, owner_headers).json()

    response = client.put(
        f"/api/products/{created['id']}", json={"name": "Surf Excel 90g (New Pack)"}, headers=owner_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Surf Excel 90g (New Pack)"

    audit = client.get(
        "/api/audit-logs", params={"entity_type": "product", "entity_id": created["id"]}, headers=owner_headers
    )
    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()]
    assert "PRODUCT_CREATED" in actions
    assert "PRODUCT_UPDATED" in actions


def test_price_change_is_audited(client, owner_headers):
    created = _create_product(client, owner_headers).json()
    client.put(f"/api/products/{created['id']}/price", json={"new_price": "120.00"}, headers=owner_headers)

    audit = client.get(
        "/api/audit-logs", params={"entity_type": "product", "entity_id": created["id"]}, headers=owner_headers
    )
    actions = [entry["action"] for entry in audit.json()]
    assert "PRICE_CHANGED" in actions


def test_employee_cannot_read_audit_logs(client, employee_headers):
    response = client.get("/api/audit-logs", headers=employee_headers)
    assert response.status_code == 403
