"""Operational dashboard using real data and existing model permissions."""

from django.contrib.admin.models import LogEntry
from django.db.models import F
from django.urls import reverse

from apps.catalog.models import Product
from apps.inventory.models import Inventory
from apps.orders.models import Order
from apps.users.models import User
from config.admin_theme import can_view


def dashboard_callback(request, context):
    cards = []
    if can_view(request, "catalog", "product"):
        cards.append(
            {
                "label": "Productos",
                "value": Product.objects.count(),
                "caption": "Productos en el catálogo",
                "icon": "inventory_2",
                "tone": "green",
                "url": reverse("admin:catalog_product_changelist"),
            }
        )
    if can_view(request, "orders", "order"):
        cards.append(
            {
                "label": "Pedidos pendientes",
                "value": Order.objects.filter(status=Order.Status.PENDING).count(),
                "caption": "Pendientes de confirmación",
                "icon": "shopping_bag",
                "tone": "orange",
                "url": reverse("admin:orders_order_changelist") + "?status__exact=PENDING",
            }
        )
    if can_view(request, "inventory", "inventory"):
        cards.append(
            {
                "label": "Stock bajo",
                "value": Inventory.objects.filter(
                    variant__is_active=True,
                    variant__product__is_active=True,
                    quantity_available__lte=F("reorder_level"),
                ).count(),
                "caption": "Variantes que requieren reposición",
                "icon": "warning",
                "tone": "red",
                "url": reverse("admin:inventory_inventory_changelist") + "?low_stock=yes",
            }
        )
    if can_view(request, "users", "user"):
        cards.append(
            {
                "label": "Clientes",
                "value": User.objects.filter(is_staff=False).count(),
                "caption": "Clientes registrados",
                "icon": "group",
                "tone": "blue",
                "url": reverse("admin:users_user_changelist") + "?is_staff__exact=0",
            }
        )
    # Show activity only for models the operator is currently allowed to inspect.
    activity = LogEntry.objects.select_related("user", "content_type").order_by("-action_time")
    visible_activity = []
    for entry in activity[:100]:
        content_type = entry.content_type
        if content_type and can_view(request, content_type.app_label, content_type.model):
            visible_activity.append(entry)
        if len(visible_activity) == 6:
            break
    orders = []
    if can_view(request, "orders", "order"):
        orders = Order.objects.select_related("user").order_by("-created_at")[:5]
    context.update(
        {
            "title": "Panel de control",
            "surnova_cards": cards,
            "surnova_activity": visible_activity,
            "surnova_recent_orders": orders,
            "surnova_first_name": request.user.first_name,
            "surnova_can_view_orders": can_view(request, "orders", "order"),
        }
    )
    return context
