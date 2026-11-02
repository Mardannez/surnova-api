import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied

from apps.inventory.models import Inventory, InventoryMovement
from apps.inventory.services.inventory_service import move_stock
from apps.orders.models import Order
from apps.orders.services.order_status_service import transition_order
from common.exceptions import Conflict

pytestmark = pytest.mark.django_db


def test_inventory_never_negative(variant):
    before = InventoryMovement.objects.count()
    for kind, qty in [("OUT", 11), ("RESERVATION", 11), ("RELEASE", 1), ("ADJUSTMENT", -11)]:
        with pytest.raises(Conflict):
            move_stock(variant_id=variant.pk, movement_type=kind, quantity=qty)
    stock = Inventory.objects.get(variant=variant)
    assert stock.quantity_available == 10 and stock.quantity_reserved == 0
    assert InventoryMovement.objects.count() == before
    with pytest.raises(IntegrityError), transaction.atomic():
        Inventory.objects.filter(pk=stock.pk).update(quantity_available=-1)


def test_cancel_releases_reserved_stock_once(customer, variant, filled_cart, address, admin_user):
    order_id = customer.post(
        "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="cancel"
    ).json()["id"]
    transition_order(order_id=order_id, new_status="CANCELLED", actor=admin_user)
    stock = Inventory.objects.get(variant=variant)
    assert (stock.quantity_available, stock.quantity_reserved) == (10, 0)
    with pytest.raises(Conflict):
        transition_order(order_id=order_id, new_status="CANCELLED", actor=admin_user)


def test_status_transitions_shipping_consumes_reservation(
    customer, variant, filled_cart, address, admin_user, user
):
    order_id = customer.post(
        "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="statuses"
    ).json()["id"]
    with pytest.raises(PermissionDenied):
        transition_order(order_id=order_id, new_status="CONFIRMED", actor=user)
    user.is_staff = True
    user.save()
    with pytest.raises(PermissionDenied):
        transition_order(order_id=order_id, new_status="CONFIRMED", actor=user)
    with pytest.raises(Conflict):
        transition_order(order_id=order_id, new_status="DELIVERED", actor=admin_user)
    for state in ["CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"]:
        transition_order(order_id=order_id, new_status=state, actor=admin_user)
    stock = Inventory.objects.get(variant=variant)
    assert (stock.quantity_available, stock.quantity_reserved) == (8, 0)
    with pytest.raises(Conflict):
        transition_order(order_id=order_id, new_status="PENDING", actor=admin_user)
    order = Order.objects.get(pk=order_id)
    order.status = "PENDING"
    with pytest.raises(ValidationError):
        order.save()
    order = transition_order(order_id=order_id, new_status="REFUNDED", actor=admin_user)
    assert order.status_history.count() == 6
    stock.refresh_from_db()
    assert stock.quantity_available == 8  # A refund does not imply a physical return.


def test_admin_access_and_readonly_fields(client, user, admin_user, customer, filled_cart, address):
    assert client.get("/admin/").status_code == 302
    client.force_login(user)
    assert client.get("/admin/").status_code == 302
    order = customer.post(
        "/api/v1/checkout/", address, format="json", HTTP_IDEMPOTENCY_KEY="admin"
    ).json()
    client.force_login(admin_user)
    assert client.get("/admin/").status_code == 200
    for path in [
        "users/user",
        "catalog/product",
        "catalog/productvariant",
        "inventory/inventory",
        "inventory/inventorymovement",
        "carts/cart",
        "orders/order",
        "orders/orderstatushistory",
    ]:
        assert client.get(f"/admin/{path}/").status_code == 200
    detail = client.get(f"/admin/orders/order/{order['id']}/change/")
    assert detail.status_code == 200
    assert b'name="total"' not in detail.content
    assert b'name="status"' not in detail.content


def test_admin_stock_movement_uses_service(client, admin_user, variant):
    client.force_login(admin_user)
    response = client.post(
        "/admin/inventory/inventorymovement/add/",
        {
            "variant": str(variant.pk),
            "movement_type": "ADJUSTMENT",
            "quantity": -2,
            "reference": "conteo",
            "notes": "Reconteo",
            "_save": "Guardar",
        },
    )
    assert response.status_code == 302
    assert Inventory.objects.get(variant=variant).quantity_available == 8
    movement = InventoryMovement.objects.get(reference="conteo")
    assert movement.created_by == admin_user
    response = client.post(
        "/admin/inventory/inventorymovement/add/",
        {
            "variant": str(variant.pk),
            "movement_type": "OUT",
            "quantity": 1000,
            "reference": "invalid",
            "notes": "",
            "_save": "Guardar",
        },
    )
    assert response.status_code == 302
    assert Inventory.objects.get(variant=variant).quantity_available == 8
    assert not InventoryMovement.objects.filter(reference="invalid").exists()
