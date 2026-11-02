from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.catalog.models import ProductVariant
from apps.inventory.models import InventoryMovement
from apps.inventory.services.inventory_service import move_stock
from apps.orders.models import Order, OrderStatusHistory
from common.exceptions import Conflict

TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.PROCESSING, Order.Status.CANCELLED},
    Order.Status.PROCESSING: {Order.Status.SHIPPED, Order.Status.CANCELLED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: {Order.Status.REFUNDED},
    Order.Status.CANCELLED: set(),
    Order.Status.REFUNDED: set(),
}


@transaction.atomic
def transition_order(*, order_id, new_status: str, actor, notes: str = "") -> Order:
    if not actor.is_active or not actor.is_staff or not actor.has_perm("orders.change_order"):
        raise PermissionDenied("Se requiere permiso administrativo para cambiar pedidos.")
    order = Order.objects.select_for_update().get(pk=order_id)
    if new_status not in TRANSITIONS[order.status]:
        raise Conflict(f"Transición inválida: {order.status} → {new_status}.")
    previous_status = order.status
    items = list(order.items.order_by("variant_id"))
    if new_status in {Order.Status.SHIPPED, Order.Status.CANCELLED}:
        if any(item.variant_id is None for item in items):
            raise Conflict("Una variante del pedido ya no está disponible para ajustar inventario.")
        list(
            ProductVariant.objects.select_for_update()
            .filter(pk__in=[i.variant_id for i in items])
            .order_by("pk")
        )
        for item in items:
            move_stock(
                variant_id=item.variant_id,
                quantity=item.quantity,
                actor=actor,
                reference=order.public_number,
                notes=notes,
                movement_type=InventoryMovement.Type.RELEASE
                if new_status == Order.Status.CANCELLED
                else InventoryMovement.Type.OUT,
                consume_reserved=new_status == Order.Status.SHIPPED,
            )
    order.status = new_status
    order._status_service = True
    order.save(update_fields=["status", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=actor,
        notes=notes,
    )
    return order
