from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.catalog.models import ProductVariant
from apps.inventory.models import Inventory, InventoryMovement
from common.exceptions import Conflict


@transaction.atomic
def move_stock(
    *,
    variant_id,
    movement_type: str,
    quantity: int,
    actor=None,
    reference: str = "",
    notes: str = "",
    consume_reserved: bool = False,
) -> Inventory:
    if type(quantity) is not int or quantity == 0:
        raise ValidationError("La cantidad debe ser un entero distinto de cero.")
    if movement_type not in InventoryMovement.Type.values:
        raise ValidationError("Tipo de movimiento inválido.")
    if movement_type != InventoryMovement.Type.ADJUSTMENT and quantity < 1:
        raise ValidationError("La cantidad debe ser positiva.")
    # All stock operations take the same variant -> inventory lock order.
    ProductVariant.objects.select_for_update().get(pk=variant_id)
    stock, _ = Inventory.objects.get_or_create(variant_id=variant_id)
    stock = Inventory.objects.select_for_update().get(pk=stock.pk)
    match movement_type:
        case InventoryMovement.Type.IN | InventoryMovement.Type.ADJUSTMENT:
            stock.quantity_available += quantity
        case InventoryMovement.Type.RESERVATION:
            stock.quantity_available -= quantity
            stock.quantity_reserved += quantity
        case InventoryMovement.Type.RELEASE:
            stock.quantity_available += quantity
            stock.quantity_reserved -= quantity
        case InventoryMovement.Type.OUT:
            if consume_reserved:
                stock.quantity_reserved -= quantity
            else:
                stock.quantity_available -= quantity
    if stock.quantity_available < 0 or stock.quantity_reserved < 0:
        raise Conflict("Inventario insuficiente para completar la operación.")
    stock.save(update_fields=["quantity_available", "quantity_reserved", "updated_at"])
    InventoryMovement.objects.create(
        variant_id=variant_id,
        movement_type=movement_type,
        quantity=quantity,
        reference=reference,
        notes=notes,
        created_by=actor,
    )
    return stock
