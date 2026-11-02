import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from common.models import TimestampedModel, UUIDModel


def public_order_number():
    return f"SN-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:16].upper()}"


class Order(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        CONFIRMED = "CONFIRMED", "Confirmado"
        PROCESSING = "PROCESSING", "En preparación"
        SHIPPED = "SHIPPED", "Enviado"
        DELIVERED = "DELIVERED", "Entregado"
        CANCELLED = "CANCELLED", "Cancelado"
        REFUNDED = "REFUNDED", "Reembolsado"

    public_number = models.CharField(
        max_length=40, unique=True, default=public_order_number, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    shipping_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True, max_length=2000)
    idempotency_key = models.CharField(max_length=128, editable=False)
    request_fingerprint = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"], name="unique_user_checkout_key"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    subtotal__gte=0,
                    discount_total__gte=0,
                    tax_total__gte=0,
                    shipping_total__gte=0,
                    total__gte=0,
                ),
                name="order_amounts_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    total=models.F("subtotal")
                    - models.F("discount_total")
                    + models.F("tax_total")
                    + models.F("shipping_total")
                ),
                name="order_total_consistent",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding and not getattr(self, "_status_service", False):
            old_status = type(self).objects.values_list("status", flat=True).get(pk=self.pk)
            if old_status != self.status:
                raise ValidationError("Utiliza order_status_service para cambiar el estado.")
        try:
            super().save(*args, **kwargs)
        finally:
            self._status_service = False

    def __str__(self):
        return self.public_number


class OrderItem(UUIDModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, on_delete=models.SET_NULL
    )
    product_name_snapshot = models.CharField(max_length=200)
    variant_name_snapshot = models.CharField(max_length=150)
    sku_snapshot = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        ordering = ["sku_snapshot"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1, unit_price__gt=0), name="order_item_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(line_total=models.F("unit_price") * models.F("quantity")),
                name="order_item_total_consistent",
            ),
        ]


class OrderAddress(UUIDModel):
    class Type(models.TextChoices):
        SHIPPING = "SHIPPING", "Envío"
        BILLING = "BILLING", "Facturación"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField(max_length=10, choices=Type.choices)
    full_name = models.CharField(max_length=250)
    phone = models.CharField(max_length=30)
    address_line_1 = models.CharField(max_length=250)
    address_line_2 = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "address_type"], name="unique_order_address_type"
            )
        ]


class OrderStatusHistory(UUIDModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=15, choices=Order.Status.choices, blank=True)
    new_status = models.CharField(max_length=15, choices=Order.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
