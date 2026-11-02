from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.services.pricing_service import cart_subtotal, line_total

from .models import Cart, CartItem


class StrictQuantityField(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            raise serializers.ValidationError("Debe ser un entero JSON.")
        return super().to_internal_value(data)


class AddItemSerializer(serializers.Serializer):
    variant = serializers.UUIDField()
    quantity = StrictQuantityField(min_value=1, max_value=100)


class UpdateItemSerializer(serializers.Serializer):
    quantity = StrictQuantityField(min_value=1, max_value=100)


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    unit_price = serializers.DecimalField(
        source="variant.price", max_digits=12, decimal_places=2, read_only=True
    )
    line_total = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DecimalField(max_digits=16, decimal_places=2))
    def get_line_total(self, obj):
        return str(line_total(obj.variant, obj.quantity))

    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant",
            "product_name",
            "variant_name",
            "quantity",
            "unit_price",
            "line_total",
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DecimalField(max_digits=18, decimal_places=2))
    def get_subtotal(self, obj):
        return str(cart_subtotal(obj.items.all()))

    @extend_schema_field(serializers.DecimalField(max_digits=18, decimal_places=2))
    def get_total(self, obj):
        return self.get_subtotal(obj)

    class Meta:
        model = Cart
        fields = ["id", "status", "items", "subtotal", "total", "updated_at"]
