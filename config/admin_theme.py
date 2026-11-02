"""SURNOVA identity and permission-aware navigation for Django Admin."""

from django.templatetags.static import static
from django.urls import reverse_lazy


def can_view(request, app_label, model_name):
    return request.user.has_perm(f"{app_label}.view_{model_name}") or request.user.has_perm(
        f"{app_label}.change_{model_name}"
    )


def nav_item(title, icon, app_label, model_name):
    return {
        "title": title,
        "icon": icon,
        "link": reverse_lazy(f"admin:{app_label}_{model_name}_changelist"),
        "permission": lambda request: can_view(request, app_label, model_name),
    }


UNFOLD = {
    "SITE_TITLE": "SURNOVA · Administración",
    "SITE_HEADER": "SURNOVA",
    "SITE_SUBHEADER": "Administración",
    "SITE_URL": reverse_lazy("admin:index"),
    "SITE_LOGO": lambda request: static("surnova/favicon.svg"),
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "type": "image/svg+xml",
            "href": lambda request: static("surnova/favicon.svg"),
        }
    ],
    "THEME": "light",
    "BORDER_RADIUS": "10px",
    "STYLES": [lambda request: static("surnova/admin.css")],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "DASHBOARD_CALLBACK": "common.admin_dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "#fcffe9",
            "100": "#f6ffc6",
            "200": "#efff95",
            "300": "#e8ff47",
            "400": "#d7ed36",
            "500": "#b5cd15",
            "600": "#7b9009",
            "700": "#59690f",
            "800": "#455217",
            "900": "#39451a",
            "950": "#1c2509",
        },
        "base": {
            "50": "#F8F8F6",
            "100": "#f0f1f2",
            "200": "#e2e5eb",
            "300": "#c5cad5",
            "400": "#8e96a8",
            "500": "#657089",
            "600": "#4d5871",
            "700": "#36425f",
            "800": "#16213E",
            "900": "#1A1A2E",
            "950": "#111222",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "items": [
                    {
                        "title": "Inicio",
                        "icon": "space_dashboard",
                        "link": reverse_lazy("admin:index"),
                    }
                ]
            },
            {
                "title": "Catálogo",
                "items": [
                    nav_item("Productos", "inventory_2", "catalog", "product"),
                    nav_item("Categorías", "category", "catalog", "category"),
                    nav_item("Marcas", "layers", "catalog", "brand"),
                    nav_item("Variantes", "style", "catalog", "productvariant"),
                    nav_item("Imágenes", "image", "catalog", "productimage"),
                ],
            },
            {
                "title": "Inventario",
                "items": [
                    nav_item("Existencias", "warehouse", "inventory", "inventory"),
                    nav_item("Movimientos", "swap_vert", "inventory", "inventorymovement"),
                ],
            },
            {
                "title": "Ventas",
                "items": [
                    nav_item("Pedidos", "shopping_bag", "orders", "order"),
                    nav_item("Carritos", "shopping_cart", "carts", "cart"),
                    nav_item("Historial de pedidos", "history", "orders", "orderstatushistory"),
                ],
            },
            {
                "title": "Personas y acceso",
                "items": [
                    nav_item("Clientes y usuarios", "group", "users", "user"),
                    nav_item("Grupos y permisos", "admin_panel_settings", "auth", "group"),
                ],
            },
        ],
    },
}
