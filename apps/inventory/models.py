from django.conf import settings
from django.db import models

from common.models import UUIDModel


class Inventory(UUIDModel):
    variant = models.OneToOneField(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="inventory"
    )
    quantity_available = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_available__gte=0),
                name="inventory_available_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_reserved__gte=0), name="inventory_reserved_nonnegative"
            ),
        ]

    def __str__(self):
        return str(self.variant)


class InventoryMovement(UUIDModel):
    class Type(models.TextChoices):
        IN = "IN", "Entrada"
        OUT = "OUT", "Salida"
        RESERVATION = "RESERVATION", "Reserva"
        RELEASE = "RELEASE", "Liberación"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="inventory_movements"
    )
    movement_type = models.CharField(max_length=15, choices=Type.choices)
    quantity = models.IntegerField()
    reference = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity=0), name="movement_quantity_nonzero"
            )
        ]
