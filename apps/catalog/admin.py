from django.contrib import admin
from django.db.models import Exists, F, Min, OuterRef, Q, Sum
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from apps.inventory.models import Inventory

from .models import Brand, Category, Product, ProductImage, ProductVariant


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    search_fields = ["name", "slug"]
    list_filter = ["is_active"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(CategoryAdmin):
    pass


class VariantInline(TabularInline):
    model = ProductVariant
    extra = 0


class ImageInline(TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = [
        "product_identity",
        "category_label",
        "catalog_price",
        "available_stock",
        "stock_status",
        "active_label",
        "featured_label",
    ]
    list_display_links = ["product_identity"]
    search_fields = ["name", "slug", "variants__sku", "brand__name"]
    search_help_text = "Buscar por producto, SKU o marca…"
    list_filter = ["is_active", "featured", "category", "brand"]
    autocomplete_fields = ["category", "brand"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VariantInline, ImageInline]
    list_filter_submit = True
    list_fullwidth = True
    change_list_template = "admin/catalog/product/change_list.html"

    def get_queryset(self, request):
        low_stock = Inventory.objects.filter(
            variant__product_id=OuterRef("pk"),
            variant__is_active=True,
            quantity_available__lte=F("reorder_level"),
        )
        return (
            super()
            .get_queryset(request)
            .select_related("category", "brand")
            .prefetch_related("images")
            .annotate(
                min_price=Min("variants__price", filter=Q(variants__is_active=True)),
                stock_amount=Sum(
                    "variants__inventory__quantity_available", filter=Q(variants__is_active=True)
                ),
                has_low_stock=Exists(low_stock),
            )
        )

    @admin.display(description="Producto", ordering="name")
    def product_identity(self, obj):
        image = next(iter(obj.images.all()), None)
        thumbnail = (
            format_html(
                '<img class="sn-product-thumb" src="{}" alt="" loading="lazy">', image.image.url
            )
            if image
            else format_html(
                '<span class="sn-product-placeholder material-symbols-outlined" aria-hidden="true">{}</span>',
                "inventory_2",
            )
        )
        return format_html(
            '<span class="sn-product-cell">{}<span><strong>{}</strong><small>{}</small></span></span>',
            thumbnail,
            obj.name,
            obj.brand.name if obj.brand else "Sin marca",
        )

    @admin.display(description="Precio desde", ordering="min_price")
    def catalog_price(self, obj):
        return f"L {obj.min_price:,.2f}" if obj.min_price is not None else "Sin variantes activas"

    @admin.display(description="Categoría", ordering="category__name")
    def category_label(self, obj):
        return obj.category.name

    @admin.display(description="Activo", boolean=True, ordering="is_active")
    def active_label(self, obj):
        return obj.is_active

    @admin.display(description="Destacado", boolean=True, ordering="featured")
    def featured_label(self, obj):
        return obj.featured

    @admin.display(description="Existencias", ordering="stock_amount")
    def available_stock(self, obj):
        return obj.stock_amount or 0

    @admin.display(description="Estado de stock")
    def stock_status(self, obj):
        if not obj.is_active:
            tone, label = "neutral", "Inactivo"
        elif not obj.stock_amount:
            tone, label = "danger", "Agotado"
        elif obj.has_low_stock:
            tone, label = "warning", "Stock bajo"
        else:
            tone, label = "success", "Disponible"
        return format_html('<span class="sn-badge sn-badge-{}">{}</span>', tone, label)

    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(
            request, extra_context={**(extra_context or {}), "title": "Productos e inventario"}
        )


@admin.register(ProductVariant)
class VariantAdmin(ModelAdmin):
    list_display = ["sku", "product", "name", "price", "is_active"]
    search_fields = ["sku", "name", "product__name"]
    list_filter = ["is_active"]
    autocomplete_fields = ["product"]


@admin.register(ProductImage)
class ImageAdmin(ModelAdmin):
    list_display = ["product", "variant", "alt_text", "is_primary", "sort_order"]
    search_fields = ["product__name", "alt_text"]
    autocomplete_fields = ["product", "variant"]
