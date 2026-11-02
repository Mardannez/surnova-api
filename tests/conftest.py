from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.inventory.models import InventoryMovement
from apps.inventory.services.inventory_service import move_stock
from apps.users.models import User


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        "ana@example.test", "Testing-password-982!", first_name="Ana", last_name="López"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        "otro@example.test", "Testing-password-719!", first_name="Otro", last_name="Cliente"
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        "admin@example.test", "Testing-admin-983!", first_name="Admin", last_name="Demo"
    )


@pytest.fixture
def customer(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def variant_factory(db):
    def create(*, price="150.25", stock=10, **kwargs):
        category, _ = Category.objects.get_or_create(slug="ropa", defaults={"name": "Ropa"})
        brand, _ = Brand.objects.get_or_create(slug="surnova", defaults={"name": "SURNOVA"})
        product = Product.objects.create(
            name=kwargs.pop("product_name", "Camiseta"),
            slug=f"producto-{uuid4().hex[:10]}",
            category=category,
            brand=brand,
            featured=kwargs.pop("featured", False),
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku=f"SKU-{uuid4().hex[:10]}",
            name="Mediana",
            price=Decimal(price),
            **kwargs,
        )
        if stock:
            move_stock(
                variant_id=variant.pk, movement_type=InventoryMovement.Type.IN, quantity=stock
            )
        return variant

    return create


@pytest.fixture
def variant(variant_factory):
    return variant_factory()


@pytest.fixture
def address():
    return {
        "addresses": [
            {
                "address_type": "SHIPPING",
                "full_name": "Ana López",
                "phone": "+50499990000",
                "address_line_1": "Casa 10",
                "city": "Tegucigalpa",
                "state": "Francisco Morazán",
                "country": "HN",
            }
        ]
    }


@pytest.fixture
def filled_cart(customer, variant):
    response = customer.post(
        "/api/v1/cart/items/", {"variant": str(variant.pk), "quantity": 2}, format="json"
    )
    assert response.status_code == 201
    return response.json()
