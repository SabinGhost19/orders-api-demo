"""Unit tests for the orders API."""

from fastapi.testclient import TestClient

from main import OrderItem, app, compute_order_total

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["service"] == "orders-api"


def test_compute_order_total():
    # 2*1500 + 1*999 = 3999
    items = [OrderItem(sku="A", qty=2, unit_price=1500), OrderItem(sku="B", qty=1, unit_price=999)]
    assert compute_order_total(items) == 3999


def test_compute_order_total_rejects_bad_input():
    import pytest

    with pytest.raises(ValueError):
        compute_order_total([])
    with pytest.raises(ValueError):
        compute_order_total([OrderItem(sku="A", qty=0, unit_price=100)])
    with pytest.raises(ValueError):
        compute_order_total([OrderItem(sku="A", qty=1, unit_price=0)])


def test_total_handler_ok():
    payload = {"items": [{"sku": "A", "qty": 2, "unit_price": 1500}], "currency": "EUR"}
    resp = client.post("/total", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3000
    assert body["currency"] == "EUR"


def test_total_handler_rejects_bad_currency():
    payload = {"items": [{"sku": "A", "qty": 1, "unit_price": 100}], "currency": "JPY"}
    resp = client.post("/total", json=payload)
    assert resp.status_code == 400


def test_orders_handler_creates_order():
    payload = {"items": [{"sku": "A", "qty": 3, "unit_price": 1000}], "currency": "USD"}
    resp = client.post("/orders", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3000
    assert body["status"] == "accepted"
    assert body["order_id"].startswith("ord-")
