from decimal import Decimal

import pytest

from apps.carts.models import Cart, CartItem
from apps.inventory.models import Inventory, InventoryMovement
from apps.orders.models import Order

pytestmark = pytest.mark.django_db


def test_checkout_current_prices_snapshots_and_idempotency(customer, variant, filled_cart, address):
    variant.price = Decimal("200.00")
    variant.save()
    response = customer.post(
        "/api/v1/checkout/",
        {**address, "total": "0.01"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="test-order-1",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total"] == "400.00" and data["items"][0]["unit_price"] == "200.00"
    assert data["items"][0]["sku_snapshot"] == variant.sku
    assert data["status_history"][0]["new_status"] == "PENDING"
    stock = Inventory.objects.get(variant=variant)
    assert (stock.quantity_available, stock.quantity_reserved) == (8, 2)
    assert not CartItem.objects.exists()
    assert Cart.objects.get(pk=filled_cart["id"]).status == "CHECKED_OUT"
    variant.price = Decimal("250.00")
    variant.name = "Nombre nuevo"
    variant.save()
    repeat = customer.post(
        "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="test-order-1"
    )
    assert repeat.status_code == 200 and repeat.json()["id"] == data["id"]
    assert repeat.json()["items"][0]["unit_price"] == "200.00"
    assert repeat.json()["items"][0]["variant_name_snapshot"] == "Mediana"
    assert Order.objects.count() == 1
    assert InventoryMovement.objects.filter(movement_type="RESERVATION").count() == 1
    conflict = customer.post(
        "/api/v1/checkout/",
        {**address, "notes": "Cambio"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="test-order-1",
    )
    assert conflict.status_code == 409


def test_insufficient_inventory_rolls_back_everything(customer, variant_factory, address):
    variants = sorted([variant_factory(stock=2), variant_factory(stock=2)], key=lambda v: v.pk)
    customer.post(
        "/api/v1/cart/items/", {"variant": str(variants[0].pk), "quantity": 1}, format="json"
    )
    customer.post(
        "/api/v1/cart/items/", {"variant": str(variants[1].pk), "quantity": 3}, format="json"
    )
    response = customer.post(
        "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="rollback"
    )
    assert response.status_code == 409
    assert not Order.objects.exists()
    assert CartItem.objects.count() == 2
    assert all(
        s.quantity_available == 2 and s.quantity_reserved == 0 for s in Inventory.objects.all()
    )
    assert not InventoryMovement.objects.filter(movement_type="RESERVATION").exists()


def test_empty_cart_missing_key_invalid_address_and_auth(customer, api, address):
    assert customer.post("/api/v1/checkout/", address, format="json").status_code == 400
    assert (
        customer.post(
            "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="empty"
        ).status_code
        == 400
    )
    assert (
        customer.post(
            "/api/v1/checkout/", {"addresses": []}, format="json", HTTP_IDEMPOTENCY_KEY="bad"
        ).status_code
        == 400
    )
    customer.force_authenticate(None)
    assert api.post("/api/v1/checkout/", address, format="json").status_code == 401


def test_inactive_variant_checkout_rejected(customer, variant, filled_cart, address):
    variant.is_active = False
    variant.save()
    assert (
        customer.post(
            "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="inactive"
        ).status_code
        == 409
    )
    assert not Order.objects.exists()


def test_orders_are_private_even_for_staff(customer, filled_cart, address, other_user, admin_user):
    order = customer.post(
        "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="private"
    ).json()
    assert customer.get(f"/api/v1/orders/{order['id']}/").status_code == 200
    for other in [other_user, admin_user]:
        customer.force_authenticate(other)
        assert customer.get("/api/v1/orders/").json()["count"] == 0
        assert customer.get(f"/api/v1/orders/{order['id']}/").status_code == 404
