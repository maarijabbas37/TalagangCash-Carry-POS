"""
Covers Phase 2 architecture review §8: payment data integrity, and the
QR payment_reference persistence requirement from §4.
"""


def _checkout(client, headers, **overrides):
    payload = {
        "items": [{"product_id": None, "quantity": "1"}],
        "payment_method": "CASH",
        "amount_received": "500.00",
    }
    payload.update(overrides)
    return client.post("/api/sales", json=payload, headers=headers)


def test_cash_payment_amount_matches_net_total(client, owner_headers, product_with_stock):
    response = _checkout(
        client,
        owner_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "3"}],
        discount_amount="10.00",
        amount_received="500.00",
    )
    body = response.json()
    payment = body["payments"][0]

    # 3 x 110.00 = 330.00, minus 10.00 discount = 320.00
    assert body["net_total"] == "320.00"
    assert payment["amount"] == "320.00"
    assert payment["amount_received"] == "500.00"
    assert payment["change_amount"] == "180.00"


def test_qr_payment_amount_matches_net_total_no_change(client, owner_headers, product_with_stock):
    response = _checkout(
        client,
        owner_headers,
        items=[{"product_id": str(product_with_stock.id), "quantity": "1"}],
        payment_method="QR",
        payment_reference="QR-ABC-123",
    )
    body = response.json()
    payment = body["payments"][0]

    assert payment["amount"] == body["net_total"]
    assert payment["amount_received"] is None
    assert payment["change_amount"] == "0.00"
    assert payment["payment_reference"] == "QR-ABC-123"


def test_payment_records_correct_user_and_counter(client, employee_headers, employee_user, counter2, product_with_stock):
    response = _checkout(
        client, employee_headers, items=[{"product_id": str(product_with_stock.id), "quantity": "1"}]
    )
    payment = response.json()["payments"][0]

    assert payment["user_id"] == str(employee_user.id)
    assert payment["counter_id"] == str(counter2.id)  # employee's default counter


def test_cash_payment_rejected_when_amount_received_missing(client, employee_headers, product_with_stock):
    response = client.post(
        "/api/sales",
        json={
            "items": [{"product_id": str(product_with_stock.id), "quantity": "1"}],
            "payment_method": "CASH",
        },
        headers=employee_headers,
    )
    assert response.status_code == 422


def test_cash_payment_rejected_when_amount_received_insufficient(client, employee_headers, product_with_stock):
    response = client.post(
        "/api/sales",
        json={
            "items": [{"product_id": str(product_with_stock.id), "quantity": "1"}],
            "payment_method": "CASH",
            "amount_received": "1.00",
        },
        headers=employee_headers,
    )
    assert response.status_code == 400
    assert "less than the total due" in response.json()["detail"].lower()
