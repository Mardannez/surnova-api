from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, connections

from apps.carts.models import CartItem
from apps.carts.services.cart_service import add_item
from apps.inventory.models import Inventory, InventoryMovement
from apps.orders.models import Order
from apps.orders.services.checkout_service import checkout
from apps.users.models import User
from common.exceptions import Conflict

pytestmark = pytest.mark.django_db(transaction=True)


def run_concurrent_checkouts(user_ids, keys, address):
    barrier = Barrier(2)

    def worker(user_id, key):
        close_old_connections()
        try:
            user = User.objects.get(pk=user_id)
            barrier.wait(timeout=15)
            order, created = checkout(user=user, idempotency_key=key, data=address)
            return str(order.pk), created
        except Conflict:
            return "conflict", False
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(worker, uid, key) for uid, key in zip(user_ids, keys, strict=True)
        ]
        return [f.result(timeout=30) for f in futures]


def test_concurrent_last_unit_cannot_be_oversold(user, other_user, variant_factory, address):
    assert connection.vendor == "postgresql", "Concurrency tests require real PostgreSQL."
    variant = variant_factory(stock=1)
    for customer in [user, other_user]:
        add_item(user=customer, token=None, variant_id=variant.pk, quantity=1)
    results = run_concurrent_checkouts([user.pk, other_user.pk], ["last-a", "last-b"], address)
    assert sum(created for _, created in results) == 1
    assert sum(order_id == "conflict" for order_id, _ in results) == 1
    assert Order.objects.count() == 1
    stock = Inventory.objects.get(variant=variant)
    assert (stock.quantity_available, stock.quantity_reserved) == (0, 1)
    assert CartItem.objects.count() == 1


def test_concurrent_same_idempotency_key_creates_one_order(user, variant, address):
    add_item(user=user, token=None, variant_id=variant.pk, quantity=1)
    results = run_concurrent_checkouts([user.pk, user.pk], ["same", "same"], address)
    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]
    assert Order.objects.count() == 1
    assert InventoryMovement.objects.filter(movement_type="RESERVATION").count() == 1
