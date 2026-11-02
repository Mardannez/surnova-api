import pytest
from django.core.management import call_command

from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import Inventory, InventoryMovement
from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_seed_is_idempotent_and_preserves_stock():
    call_command("seed_demo")
    variant = ProductVariant.objects.get(sku="SN-CAM-M")
    Inventory.objects.filter(variant=variant).update(quantity_available=3)
    count = InventoryMovement.objects.count()
    call_command("seed_demo")
    assert Product.objects.count() == 2
    assert ProductVariant.objects.count() == 3
    assert User.objects.filter(email="cliente@example.test").count() == 1
    assert Inventory.objects.get(variant=variant).quantity_available == 3
    assert InventoryMovement.objects.count() == count
    assert not User.objects.get(email="cliente@example.test").has_usable_password()


def test_schema_docs_redoc_and_json_404(api):
    schema = api.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert schema.status_code == 200
    document = schema.json()
    assert "/api/v1/checkout/" in document["paths"]
    assert "jwtAuth" in document["components"]["securitySchemes"]
    assert api.get("/api/docs/").status_code == 200
    assert api.get("/api/redoc/").status_code == 200
    response = api.get("/not-found/")
    assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_cors_supports_cart_token_and_idempotency(api, settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    response = api.options(
        "/api/v1/checkout/",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,idempotency-key,x-cart-token",
    )
    assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "idempotency-key" in response["Access-Control-Allow-Headers"]
    assert "X-Cart-Token" in response["Access-Control-Expose-Headers"]
