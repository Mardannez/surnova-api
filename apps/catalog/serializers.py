from rest_framework import serializers

from .models import Brand, Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug"]


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "name", "price", "compare_at_price", "attributes"]


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "variant", "image", "alt_text", "sort_order", "is_primary"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    variants = VariantSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "brand",
            "name",
            "slug",
            "short_description",
            "description",
            "featured",
            "price",
            "variants",
            "images",
            "created_at",
        ]
