from starlette.testclient import TestClient


def test_seeded_orders_are_listed(client: TestClient) -> None:
    response = client.get("/orders")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    assert len(body["items"]) == body["total"]
    assert all(item["status"] == "pending_verification" for item in body["items"])


def test_create_and_fetch_order(client: TestClient) -> None:
    payload = {
        "customer_name": "Aman",
        "phone": "+919999999999",
        "product_summary": "Yoga Mat 6mm",
        "order_value": 799,
        "address_short": "Koramangala, Bengaluru 560034",
        "scheduled_slot": "10 May, evening",
        "brand_name": "RetailKart",
    }
    response = client.post("/orders", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["customer_name"] == "Aman"
    assert created["status"] == "pending_verification"

    fetched = client.get(f"/orders/{created['id']}").json()
    assert fetched["id"] == created["id"]
    assert fetched["product_summary"] == "Yoga Mat 6mm"


def test_missing_order_returns_404(client: TestClient) -> None:
    response = client.get("/orders/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "ORDER_NOT_FOUND"
