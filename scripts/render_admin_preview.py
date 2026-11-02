"""Render real Admin templates with disposable data in an isolated test database.

Run: python scripts/render_admin_preview.py
The generated pages contain demo data only; test sessions are destroyed on completion.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.admin.models import ADDITION, LogEntry  # noqa: E402
from django.contrib.contenttypes.models import ContentType  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_databases, teardown_databases  # noqa: E402

from apps.carts.services.cart_service import add_item  # noqa: E402
from apps.catalog.models import Product, ProductVariant  # noqa: E402
from apps.inventory.services.inventory_service import move_stock  # noqa: E402
from apps.orders.services.checkout_service import checkout  # noqa: E402
from apps.users.models import User  # noqa: E402

settings.DATABASES["default"].setdefault("TEST", {})["NAME"] = "test_surnova_admin_visual"
database_config = setup_databases(verbosity=0, interactive=False)
try:
    call_command("seed_demo", verbosity=0)
    operator = User.objects.create_superuser(
        email="diseno@example.test", password=None, first_name="Daniel", last_name="Demo"
    )
    customer = User.objects.get(email="cliente@example.test")
    variant = ProductVariant.objects.get(sku="SN-CAM-M")
    add_item(user=customer, token=None, variant_id=variant.pk, quantity=2)
    order, _ = checkout(
        user=customer,
        idempotency_key="visual-preview",
        data={
            "addresses": [
                {
                    "address_type": "SHIPPING",
                    "full_name": "Cliente Demo",
                    "phone": "+50499990000",
                    "address_line_1": "Colonia Centro, casa 10",
                    "city": "Tegucigalpa",
                    "state": "Francisco Morazán",
                    "country": "HN",
                }
            ],
            "notes": "Pedido de demostración visual",
        },
    )
    move_stock(
        variant_id=ProductVariant.objects.get(sku="SN-MOC-NEG").pk,
        movement_type="ADJUSTMENT",
        quantity=-23,
        actor=operator,
        reference="Vista de demostración",
    )
    content_type = ContentType.objects.get_for_model(Product)
    for product in Product.objects.all():
        LogEntry.objects.create(
            user=operator,
            content_type=content_type,
            object_id=str(product.pk),
            object_repr=product.name,
            action_flag=ADDITION,
        )
    client = Client(HTTP_HOST="127.0.0.1")
    client.force_login(operator)
    output = ROOT / ".artifacts" / "admin-preview"
    output.mkdir(parents=True, exist_ok=True)
    pages = {
        "index": "/admin/",
        "products": "/admin/catalog/product/",
        "order": f"/admin/orders/order/{order.pk}/change/",
        "product-form": f"/admin/catalog/product/{variant.product_id}/change/",
    }
    for name, url in pages.items():
        response = client.get(url)
        if response.status_code != 200:
            raise RuntimeError(f"Cannot render {name}: {response.status_code}")
        html = response.content.decode("utf-8").replace(
            "<head>", '<head><meta charset="utf-8"><base href="http://127.0.0.1:8765/">', 1
        )
        (output / f"{name}.html").write_text(html, encoding="utf-8")
    client.logout()
    response = client.get("/admin/login/")
    (output / "login.html").write_text(
        response.content.decode("utf-8").replace(
            "<head>", '<head><meta charset="utf-8"><base href="http://127.0.0.1:8765/">', 1
        ),
        encoding="utf-8",
    )
    print("Admin previews rendered in .artifacts/admin-preview; disposable database removed.")
finally:
    teardown_databases(database_config, verbosity=0)
