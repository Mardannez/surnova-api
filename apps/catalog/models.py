from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimestampedModel, UUIDModel
from common.validators import validate_image


class Category(TimestampedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="categories/%Y/%m/", blank=True, validators=[validate_image]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Brand(UUIDModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Product(TimestampedModel):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [models.Index(fields=["is_active", "featured", "created_at"])]

    def __str__(self):
        return self.name


class ProductVariant(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sku"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="variant_positive_price"),
            models.CheckConstraint(
                condition=models.Q(compare_at_price__isnull=True)
                | models.Q(compare_at_price__gte=models.F("price")),
                name="variant_compare_at_gte_price",
            ),
        ]

    def clean(self):
        if not isinstance(self.attributes, dict):
            raise ValidationError({"attributes": "Debe ser un objeto JSON."})
        if (
            self.compare_at_price is not None
            and self.price is not None
            and self.compare_at_price < self.price
        ):
            raise ValidationError({"compare_at_price": "Debe ser mayor o igual al precio."})

    def __str__(self):
        return f"{self.sku} — {self.name}"


class ProductImage(UUIDModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    variant = models.ForeignKey(
        ProductVariant, null=True, blank=True, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/%Y/%m/", validators=[validate_image])
    alt_text = models.CharField(max_length=250, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="one_primary_product_image",
            )
        ]

    def clean(self):
        if self.variant_id and self.variant.product_id != self.product_id:
            raise ValidationError({"variant": "La variante debe pertenecer al producto."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
