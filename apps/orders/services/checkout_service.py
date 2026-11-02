import hashlib
import json

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.carts.models import Cart
from apps.carts.services.cart_service import get_cart
from apps.catalog.models import ProductVariant
from apps.catalog.services.pricing_service import cart_subtotal, line_total
from apps.inventory.models import InventoryMovement
from apps.inventory.services.inventory_service import move_stock
from apps.orders.models import Order, OrderAddress, OrderItem, OrderStatusHistory
from apps.users.models import User
from common.exceptions import Conflict


@transaction.atomic
def checkout(*, user, idempotency_key: str, data: dict, cart_token=None) -> tuple[Order, bool]:
    if (
        not idempotency_key
        or len(idempotency_key) > 128
        or not idempotency_key.isascii()
        or any(ord(c) < 33 or ord(c) > 126 for c in idempotency_key)
    ):
        raise ValidationError(
            {"idempotency_key": "Envía Idempotency-Key de 1 a 128 caracteres ASCII visibles."}
        )
    fingerprint = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    User.objects.select_for_update(no_key=True).get(pk=user.pk)
    previous = Order.objects.filter(user=user, idempotency_key=idempotency_key).first()
    if previous:
        if previous.request_fingerprint != fingerprint:
            raise Conflict("Esta clave de idempotencia ya se utilizó con otros datos.")
        return previous, False
    cart = get_cart(user=user, token=cart_token)
    items = list(cart.items.order_by("variant_id"))
    if not items:
        raise ValidationError({"cart": "El carrito está vacío."})
    # Deterministic locking across carts prevents overselling and lock-order deadlocks.
    variants = {
        v.pk: v
        for v in ProductVariant.objects.select_for_update()
        .filter(pk__in=[i.variant_id for i in items])
        .order_by("pk")
    }
    for item in items:
        variant = variants[item.variant_id]
        product = variant.product
        if (
            not variant.is_active
            or not product.is_active
            or not product.category.is_active
            or (product.brand_id and not product.brand.is_active)
        ):
            raise Conflict("El carrito contiene productos no disponibles.")
        item.variant = variant
    subtotal = cart_subtotal(items)
    order = Order.objects.create(
        user=user,
        subtotal=subtotal,
        total=subtotal,
        notes=data.get("notes", ""),
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    for item in items:
        variant = item.variant
        move_stock(
            variant_id=variant.pk,
            movement_type=InventoryMovement.Type.RESERVATION,
            quantity=item.quantity,
            actor=user,
            reference=order.public_number,
        )
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name_snapshot=variant.product.name,
            variant_name_snapshot=variant.name,
            sku_snapshot=variant.sku,
            unit_price=variant.price,
            quantity=item.quantity,
            line_total=line_total(variant, item.quantity),
        )
    for address in data["addresses"]:
        OrderAddress.objects.create(order=order, **address)
    OrderStatusHistory.objects.create(
        order=order, previous_status="", new_status=order.status, changed_by=user
    )
    cart.status = Cart.Status.CHECKED_OUT
    cart.save(update_fields=["status", "updated_at"])
    cart.items.all().delete()
    return order, True
