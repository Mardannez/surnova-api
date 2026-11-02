import pytest
from django.contrib.auth.models import Permission

from apps.catalog.models import ProductVariant
from apps.inventory.models import Inventory, InventoryMovement
from apps.inventory.services.inventory_service import move_stock
from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_dashboard_uses_real_metrics_and_model_permissions(client, admin_user, variant, user):
    client.force_login(admin_user)
    response = client.get("/admin/")
    assert response.status_code == 200
    metrics = {card["label"]: card["value"] for card in response.context["surnova_cards"]}
    assert metrics == {"Productos": 1, "Pedidos pendientes": 0, "Stock bajo": 0, "Clientes": 1}
    Inventory.objects.filter(variant=variant).update(quantity_available=1)
    response = client.get("/admin/")
    assert (
        next(card for card in response.context["surnova_cards"] if card["label"] == "Stock bajo")[
            "value"
        ]
        == 1
    )

    user.is_staff = True
    user.save()
    user.user_permissions.add(
        Permission.objects.get(codename="view_product", content_type__app_label="catalog")
    )
    client.force_login(user)
    restricted = client.get("/admin/")
    assert [card["label"] for card in restricted.context["surnova_cards"]] == ["Productos"]
    assert not restricted.context["surnova_recent_orders"]
    assert b'href="/admin/users/user/"' not in restricted.content
    assert b'href="/admin/orders/order/"' not in restricted.content


def test_product_stock_summary_and_low_stock_filter(client, admin_user, variant):
    extra = ProductVariant.objects.create(
        product=variant.product, sku="SECOND-ACTIVE", name="Grande", price="200.00"
    )
    move_stock(variant_id=extra.pk, movement_type=InventoryMovement.Type.IN, quantity=3)
    client.force_login(admin_user)
    response = client.get("/admin/catalog/product/")
    assert response.status_code == 200
    product = response.context["cl"].result_list[0]
    assert product.stock_amount == 13 and product.min_price == variant.price
    assert product.has_low_stock
    assert b"sn-badge-warning" in response.content
    low = client.get("/admin/inventory/inventory/?low_stock=yes")
    assert list(low.context["cl"].result_list.values_list("variant_id", flat=True)) == [extra.pk]


def test_custom_user_forms_create_and_change_password(client, admin_user):
    client.force_login(admin_user)
    assert client.get("/admin/users/user/add/").status_code == 200
    response = client.post(
        "/admin/users/user/add/",
        {
            "email": "operador@example.test",
            "first_name": "Operador",
            "last_name": "Demo",
            "password1": "Operator-secret-549!",
            "password2": "Operator-secret-549!",
            "usable_password": "true",
            "_save": "Guardar",
        },
    )
    assert response.status_code == 302
    operator = User.objects.get(email="operador@example.test")
    assert operator.check_password("Operator-secret-549!") and not operator.is_superuser
    assert client.get(f"/admin/users/user/{operator.pk}/password/").status_code == 200
