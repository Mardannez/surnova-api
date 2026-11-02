from rest_framework import serializers

from .models import Order, OrderAddress, OrderItem, OrderStatusHistory


class AddressSerializer(serializers.ModelSerializer):
    country = serializers.RegexField(
        r"^[A-Za-z]{2}$", max_length=2, help_text="Código ISO 3166-1 alpha-2, por ejemplo HN."
    )

    def validate_country(self, value):
        return value.upper()

    class Meta:
        model = OrderAddress
        exclude = ["id", "order"]
        validators = []


class CheckoutSerializer(serializers.Serializer):
    addresses = AddressSerializer(many=True, min_length=1, max_length=2)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")

    def validate_addresses(self, value):
        types = [a["address_type"] for a in value]
        if len(set(types)) != len(types) or "SHIPPING" not in types:
            raise serializers.ValidationError(
                "Incluye una dirección SHIPPING y como máximo una BILLING."
            )
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        exclude = ["order"]


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["previous_status", "new_status", "notes", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    addresses = AddressSerializer(many=True, read_only=True)
    status_history = HistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "public_number",
            "status",
            "subtotal",
            "discount_total",
            "tax_total",
            "shipping_total",
            "total",
            "notes",
            "items",
            "addresses",
            "status_history",
            "created_at",
            "updated_at",
        ]
