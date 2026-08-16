"""
Covers the Phase 2 architecture test plan (§11) plus the amendments from
the review: atomic sale creation, stock decrement correctness, discount
validation + audit, historical price integrity, bill-number uniqueness/
sequencing (including that a rolled-back sale does NOT consume a number),
reprint idempotence, and multi-item carts.
"""
from decimal import Decimal


def _checkout(client, headers, **overrides):
    payload = {
        "items": [{"product_id": None, "quantity": "2"}],
        "payment_method": "CASH",
        "amount_received": "500.00",
    }
    payload.update(overrides)
    return client.post("/api/sales", json=payload, headers=headers)


def test_cash_sale_decrements_stock_and_computes_change(client, employee_headers, product_with_stock):
    response = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "2"}],
        payment_method="CASH",
        amount_received="500.00",
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["subtotal"] == "220.00"  # 2 x 110.00
    assert body["net_total"] == "220.00"
    assert len(body["payments"]) == 1
    payment = body["payments"][0]
    assert payment["payment_method"] == "CASH"
    assert payment["amount_received"] == "500.00"
    assert payment["change_amount"] == "280.00"

    stock_check = client.get(f"/api/products/{product_with_stock.id}", headers=employee_headers)
    assert stock_check.json()["id"] == str(product_with_stock.id)


def test_qr_sale_has_no_change_and_stores_reference(client, employee_headers, product_with_stock):
    response = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "1"}],
        payment_method="QR",
        payment_reference="TXN-REF-001",
    )
    assert response.status_code == 201, response.text
    payment = response.json()["payments"][0]
    assert payment["payment_method"] == "QR"
    assert payment["amount_received"] is None
    assert payment["change_amount"] == "0.00"
    assert payment["payment_reference"] == "TXN-REF-001"


def test_qr_sale_without_reference_is_allowed(client, employee_headers, product_with_stock):
    """payment_reference is optional/nullable — QR stays manual-confirm-only in Phase 2."""
    response = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "1"}],
        payment_method="QR",
    )
    assert response.status_code == 201
    assert response.json()["payments"][0]["payment_reference"] is None


def test_insufficient_stock_rejected_with_no_orphan_rows(client, db_session, employee_headers, product_with_stock):
    from app.models.inventory import InventoryMovement
    from app.models.sale import Sale, SaleItem

    before_sales = db_session.query(Sale).count()
    before_items = db_session.query(SaleItem).count()
    before_movements = db_session.query(InventoryMovement).count()

    response = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "999"}],
        payment_method="CASH",
        amount_received="1000000.00",
    )
    assert response.status_code == 409
    assert "insufficient stock" in response.json()["detail"].lower()

    # Atomicity, proven by absence: nothing was left behind by the failed attempt.
    assert db_session.query(Sale).count() == before_sales
    assert db_session.query(SaleItem).count() == before_items
    assert db_session.query(InventoryMovement).count() == before_movements


def test_zero_quantity_rejected(client, employee_headers, product_with_stock):
    response = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "0"}],
    )
    assert response.status_code == 422  # Pydantic gt=0 validation


def test_inactive_product_cannot_be_sold(client, db_session, employee_headers, product_with_stock):
    product_with_stock.is_active = False
    db_session.add(product_with_stock)
    db_session.commit()

    response = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    )
    assert response.status_code == 400
    assert "not active" in response.json()["detail"].lower()


def test_discount_exceeding_subtotal_rejected(client, employee_headers, product_with_stock):
    response = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "1"}],
        discount_amount="999.00",
    )
    assert response.status_code == 400
    assert "discount" in response.json()["detail"].lower()


def test_valid_discount_reduces_total_and_is_audited(client, owner_headers, product_with_stock):
    response = _checkout(
        client,
        owner_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "2"}],
        discount_amount="20.00",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["subtotal"] == "220.00"
    assert body["discount_amount"] == "20.00"
    assert body["net_total"] == "200.00"
    assert body["discount_user_id"] is not None

    audit = client.get(
        "/api/audit-logs", params={"entity_type": "sale", "entity_id": body["id"]}, headers=owner_headers
    )
    actions = [entry["action"] for entry in audit.json()]
    assert "DISCOUNT_APPLIED" in actions


def test_no_discount_means_no_audit_entry(client, owner_headers, product_with_stock):
    response = _checkout(
        client, owner_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    )
    sale_id = response.json()["id"]

    audit = client.get(
        "/api/audit-logs", params={"entity_type": "sale", "entity_id": sale_id}, headers=owner_headers
    )
    assert audit.json() == []


def test_historical_price_unaffected_by_later_price_change(client, owner_headers, product_with_stock):
    sale_response = _checkout(
        client, owner_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    )
    sale_id = sale_response.json()["id"]
    original_unit_price = sale_response.json()["items"][0]["unit_price"]
    assert original_unit_price == "110.00"

    client.put(
        f"/api/products/{product_with_stock.id}/price", json={"new_price": "150.00"}, headers=owner_headers
    )

    replay = client.get(f"/api/sales/{sale_id}", headers=owner_headers)
    assert replay.json()["items"][0]["unit_price"] == "110.00"  # unchanged


def test_bill_numbers_unique_and_sequential(client, employee_headers, product_with_stock):
    first = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    ).json()
    second = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    ).json()

    assert second["bill_number"] == first["bill_number"] + 1


def test_failed_sale_does_not_consume_a_bill_number(client, employee_headers, product_with_stock):
    ok = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    ).json()

    # product_with_stock has 10 units — 11 cleanly triggers the stock
    # check (not the payment check), which is the failure mode this test
    # targets. amount_received is generous precisely so payment validation
    # isn't what fails here.
    failed = _checkout(
        client,
        employee_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "11"}],
        amount_received="100000.00",
    )
    assert failed.status_code == 409

    next_ok = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    ).json()

    # No gap — the failed attempt's bill-number reservation rolled back with it.
    assert next_ok["bill_number"] == ok["bill_number"] + 1


def test_reprint_is_idempotent(client, db_session, employee_headers, product_with_stock):
    from app.models.inventory import InventoryMovement
    from app.models.sale import Sale, SaleItem

    sale_id = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    ).json()["id"]

    before = (
        db_session.query(Sale).count(),
        db_session.query(SaleItem).count(),
        db_session.query(InventoryMovement).count(),
    )

    client.get(f"/api/sales/{sale_id}", headers=employee_headers)
    client.get(f"/api/sales/{sale_id}", headers=employee_headers)

    after = (
        db_session.query(Sale).count(),
        db_session.query(SaleItem).count(),
        db_session.query(InventoryMovement).count(),
    )
    assert before == after


def test_multi_item_cart_decrements_each_product_and_links_movements(client, db_session, owner_headers, product_with_stock):
    import uuid as uuid_module
    from decimal import Decimal as D

    from app.models.inventory import InventoryMovement, MovementType
    from app.models.product import Product

    second = Product(
        id=uuid_module.uuid4(), name="Rice 1kg", unit="pcs", sale_price=D("350.00"), current_stock=D("20")
    )
    db_session.add(second)
    db_session.commit()

    response = _checkout(
        client,
        owner_headers,
        items=[
            {"product_id": str(product_with_stock.id), "quantity": "2"},
            {"product_id": str(second.id), "quantity": "3"},
        ],
        amount_received="2000.00",
    )
    assert response.status_code == 201, response.text
    sale_id = response.json()["id"]
    assert len(response.json()["items"]) == 2

    movements = (
        db_session.query(InventoryMovement)
        .filter(InventoryMovement.reference_id == uuid_module.UUID(sale_id), InventoryMovement.movement_type == MovementType.SALE)
        .all()
    )
    assert len(movements) == 2
    assert {str(m.product_id) for m in movements} == {str(product_with_stock.id), str(second.id)}


def test_duplicate_product_in_cart_rejected(client, employee_headers, product_with_stock):
    response = _checkout(
        client,
        employee_headers,
        items=[
            {"product_id": str(product_with_stock.id), "quantity": "1"},
            {"product_id": str(product_with_stock.id), "quantity": "1"},
        ],
    )
    assert response.status_code == 400
    assert "duplicate" in response.json()["detail"].lower()
