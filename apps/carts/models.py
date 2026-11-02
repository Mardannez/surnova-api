from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import TimestampedModel


class Cart(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        CHECKED_OUT = "CHECKED_OUT", "Cerrado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    session_key = models.CharField(max_length=64, null=True, blank=True, unique=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="ACTIVE", user__isnull=False),
                name="one_active_cart_per_user",
            ),
            models.CheckConstraint(
                condition=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name="cart_requires_owner",
            ),
        ]


class CartItem(TimestampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="unique_cart_variant"),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1, quantity__lte=100), name="cart_quantity_range"
            ),
        ]
