from django.contrib import admin, messages
from django.utils.html import format_html
from rest_framework.exceptions import APIException
from unfold.admin import ModelAdmin, TabularInline

from .models import Order, OrderAddress, OrderItem, OrderStatusHistory
from .services.order_status_service import transition_order


class ReadOnlyInline(TabularInline):
    extra = 0
    can_delete = False
    classes = ["collapse"]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


class ItemInline(ReadOnlyInline):
    model = OrderItem
    verbose_name_plural = "Detalle histórico de productos"


class AddressInline(ReadOnlyInline):
    model = OrderAddress
    verbose_name_plural = "Direcciones registradas"


class HistoryInline(ReadOnlyInline):
    model = OrderStatusHistory
    verbose_name_plural = "Historial completo del pedido"


def status_action(new_status):
    @admin.action(description=f"Cambiar a {new_status}", permissions=["change"])
    def action(modeladmin, request, queryset):
        for order in queryset.order_by("pk"):
            try:
                transition_order(
                    order_id=order.pk,
                    new_status=new_status,
                    actor=request.user,
                    notes="Acción de Django Admin",
                )
            except APIException as exc:
                modeladmin.message_user(
                    request, f"{order.public_number}: {exc.detail}", level=messages.ERROR
                )

    action.__name__ = f"set_{new_status.lower()}"
    return action


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ["public_number", "user", "status_badge", "total", "created_at"]
    search_fields = ["public_number", "user__email", "items__sku_snapshot"]
    list_filter = ["status", "created_at"]
    inlines = [ItemInline, AddressInline, HistoryInline]
    actions = [status_action(s) for s in Order.Status.values if s != "PENDING"]
    exclude = ["idempotency_key", "request_fingerprint"]
    change_form_template = "admin/orders/order/change_form.html"
    list_filter_submit = True
    list_fullwidth = True
    fieldsets = (
        ("Notas del pedido", {"fields": ("notes",)}),
        (
            "Información de auditoría",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("items", "addresses", "status_history")
        )

    @admin.display(description="Estado", ordering="status")
    def status_badge(self, obj):
        tones = {
            "PENDING": "warning",
            "CONFIRMED": "info",
            "PROCESSING": "info",
            "SHIPPED": "info",
            "DELIVERED": "success",
            "CANCELLED": "danger",
            "REFUNDED": "neutral",
        }
        return format_html(
            '<span class="sn-badge sn-badge-{}">{}</span>',
            tones.get(obj.status, "neutral"),
            obj.get_status_display(),
        )

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if obj:
            context.update(
                {
                    "show_save": False,
                    "show_save_and_continue": False,
                    "show_save_and_add_another": False,
                }
            )
            context.update(
                {
                    "surnova_order": obj,
                    "surnova_shipping_address": next(
                        (a for a in obj.addresses.all() if a.address_type == "SHIPPING"), None
                    ),
                    "surnova_order_badge": self.status_badge(obj),
                }
            )
        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields if f.name not in self.exclude]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderStatusHistory)
class HistoryAdmin(ModelAdmin):
    list_display = ["order", "previous_status", "new_status", "changed_by", "created_at"]
    search_fields = ["order__public_number"]
    list_filter = ["new_status"]
    readonly_fields = [f.name for f in OrderStatusHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
