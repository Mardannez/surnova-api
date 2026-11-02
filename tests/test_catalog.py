from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalog.models import ProductImage, ProductVariant
from common.validators import validate_image

pytestmark = pytest.mark.django_db


def test_product_filters_search_and_ordering(api, variant_factory):
    cheap = variant_factory(price="100.00", featured=True, product_name="Algodón")
    expensive = variant_factory(price="400.00", product_name="Abrigo")
    variant_factory(is_active=False)
    assert api.get("/api/v1/products/").json()["count"] == 2
    for params in [
        {"category": "ropa", "brand": "surnova", "min_price": 90, "max_price": 200},
        {"featured": "true"},
        {"search": cheap.sku},
        {"search": "Algodón"},
    ]:
        response = api.get("/api/v1/products/", params)
        assert response.status_code == 200
        assert [p["id"] for p in response.json()["results"]] == [str(cheap.product_id)]
    results = api.get("/api/v1/products/", {"ordering": "-price"}).json()["results"]
    assert results[0]["id"] == str(expensive.product_id)
    assert (
        api.get(f"/api/v1/products/{cheap.product.slug}/").json()["variants"][0]["sku"] == cheap.sku
    )
    assert api.get("/api/v1/products/", {"page_size": 9999}).json()["count"] == 2
    assert api.get("/api/v1/products/", {"min_price": "bad"}).status_code == 400


def test_hidden_variants_images_and_categories(api, variant):
    hidden = ProductVariant.objects.create(
        product=variant.product, sku="HIDDEN-SKU", name="Oculta", price="90", is_active=False
    )
    ProductImage.objects.create(product=variant.product, variant=hidden, image="hidden.png")
    response = api.get(f"/api/v1/products/{variant.product.slug}/").json()
    assert len(response["variants"]) == 1 and not response["images"]
    assert api.get("/api/v1/products/", {"search": hidden.sku}).json()["count"] == 0
    ProductVariant.objects.create(
        product=variant.product, sku="ACTIVE-SECOND", name="Grande", price="200.00"
    )
    found = api.get("/api/v1/products/", {"search": variant.product.name}).json()
    assert found["count"] == 1 and found["results"][0]["price"] == "150.25"
    assert api.get("/api/v1/products/", {"search": "ACTIVE-SECOND"}).json()["count"] == 1
    category = variant.product.category
    category.is_active = False
    category.save()
    assert api.get("/api/v1/products/").json()["count"] == 0
    assert api.get(f"/api/v1/products/{variant.product.slug}/").status_code == 404
    assert api.get("/api/v1/categories/").json()["count"] == 0


def test_public_catalog_is_read_only(api, customer, variant):
    assert api.post("/api/v1/products/", {}, format="json").status_code == 405
    assert (
        customer.patch(
            f"/api/v1/products/{variant.product.slug}/", {"name": "Hack"}, format="json"
        ).status_code
        == 405
    )


def test_image_validation_and_variant_relation(variant, variant_factory):
    with pytest.raises(ValidationError):
        validate_image(SimpleUploadedFile("fake.png", b"not an image"))
    with pytest.raises(ValidationError):
        validate_image(SimpleUploadedFile("payload.svg", b"<svg/>"))
    output = BytesIO()
    Image.new("RGB", (2, 2)).save(output, format="PNG")
    validate_image(SimpleUploadedFile("valid.png", output.getvalue()))
    other = variant_factory()
    with pytest.raises(ValidationError):
        ProductImage(product=variant.product, variant=other, image="x.png").clean()
