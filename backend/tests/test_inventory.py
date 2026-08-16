"""
Covers Phase 2 architecture review §1 (reconciliation), §2 (opening
stock guardrails), and §6 (negative-stock protection at both the
service layer and, where SQLite's CHECK-constraint support allows it,
the DB layer too — the authoritative proof against real Postgres lives
in the deployment verification, not here, since SQLite's locking model
doesn't meaningfully exercise concurrent writes).
"""
from decimal import Decimal


def test_owner_can_record_opening_stock(client, owner_headers):
    product = client.post(
        "/api/products",
        json={"name": "Pepsi 1.5L", "unit": "pcs", "sale_price": "180.00"},
        headers=owner_headers,
    ).json()

    response = client.post(
        "/api/inventory/opening-stock",
        json={"product_id": product["id"], "quantity": "50", "notes": "Initial catalog setup"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    assert response.json()["current_stock"] == "50.000"


def test_employee_cannot_record_opening_stock(client, employee_headers):
    """
    Phase 2 review amendment 2, explicitly: employees must never be able
    to call this — it's initialization/migration stock, not a normal
    recurring inventory-entry mechanism.
    """
    product = client.post(
        "/api/products",
        json={"name": "Pepsi 1.5L", "unit": "pcs", "sale_price": "180.00"},
        headers=employee_headers,
    ).json()

    response = client.post(
        "/api/inventory/opening-stock",
        json={"product_id": product["id"], "quantity": "50"},
        headers=employee_headers,
    )
    assert response.status_code == 403


def test_opening_stock_creates_movement_and_audit_entry(client, owner_headers):
    product = client.post(
        "/api/products", json={"name": "Noodles", "unit": "pcs", "sale_price": "150.00"}, headers=owner_headers
    ).json()

    client.post(
        "/api/inventory/opening-stock",
        json={"product_id": product["id"], "quantity": "30", "notes": "onboarding"},
        headers=owner_headers,
    )

    movements = client.get(f"/api/inventory/{product['id']}", headers=owner_headers).json()
    assert len(movements) == 1
    assert movements[0]["movement_type"] == "OPENING_STOCK"
    assert movements[0]["quantity"] == "30.000"

    audit = client.get(
        "/api/audit-logs", params={"entity_type": "product", "entity_id": product["id"]}, headers=owner_headers
    ).json()
    actions = [entry["action"] for entry in audit]
    assert "OPENING_STOCK_RECORDED" in actions


def test_reconciliation_reports_no_discrepancy_when_consistent(client, owner_headers, product_with_stock):
    response = client.get("/api/inventory/reconciliation/report", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["discrepancies"] == []
    assert body["products_checked"] >= 1


def test_reconciliation_detects_drift_between_ledger_and_current_stock(client, db_session, owner_headers, product_with_stock):
    """
    Deliberately corrupt current_stock via a raw field write (bypassing
    adjust_stock entirely) to simulate exactly the failure mode the
    reconciliation tool exists to catch — a drift that should be
    structurally impossible but isn't provably so without a detector.
    """
    product_with_stock.current_stock = Decimal("999")  # ledger still says 10
    db_session.add(product_with_stock)
    db_session.commit()

    response = client.get("/api/inventory/reconciliation/report", headers=owner_headers)
    body = response.json()
    assert len(body["discrepancies"]) == 1
    row = body["discrepancies"][0]
    assert row["product_id"] == str(product_with_stock.id)
    assert row["current_stock"] == "999.000"
    assert row["ledger_stock"] == "10.000"
    assert row["difference"] == "989.000"


def test_employee_cannot_view_reconciliation_report(client, employee_headers):
    response = client.get("/api/inventory/reconciliation/report", headers=employee_headers)
    assert response.status_code == 403


def test_negative_stock_rejected_at_service_layer(client, employee_headers, product_with_stock):
    """product_with_stock has 10 units — attempting to sell 11 must be rejected."""
    response = client.post(
        "/api/sales",
        json={
            "items": [{"product_id": str(product_with_stock.id), "quantity": "11"}],
            "payment_method": "CASH",
            "amount_received": "10000.00",
        },
        headers=employee_headers,
    )
    assert response.status_code == 409
    assert "insufficient stock" in response.json()["detail"].lower()
    assert "available quantity: 10" in response.json()["detail"].lower()


def test_negative_stock_rejected_at_database_layer_even_bypassing_service(db_session, product_with_stock):
    """
    The authoritative negative-stock test runs against real Postgres (see
    deployment verification) since that's where the CHECK constraint's
    guarantee actually matters. This SQLite-side test confirms the same
    constraint is at least declared and enforced here too, as a second,
    faster signal if it's ever accidentally dropped from a model change.
    """
    import pytest
    from sqlalchemy.exc import IntegrityError

    product_with_stock.current_stock = Decimal("-1")
    db_session.add(product_with_stock)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
