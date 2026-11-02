import pytest

from apps.carts.models import CartItem

pytestmark = pytest.mark.django_db


def test_server_prices_duplicate_variant_and_clear(customer, variant):
    payload = {"variant": str(variant.pk), "quantity": 2, "price": "0.01", "total": "0.01"}
    response = customer.post("/api/v1/cart/items/", payload, format="json")
    assert response.status_code == 201 and response.json()["total"] == "300.50"
    response = customer.post("/api/v1/cart/items/", payload, format="json")
    assert response.json()["total"] == "601.00"
    assert len(response.json()["items"]) == 1 and response.json()["items"][0]["quantity"] == 4
    item_id = response.json()["items"][0]["id"]
    assert (
        customer.patch(f"/api/v1/cart/items/{item_id}/", {"quantity": 1}, format="json").json()[
            "total"
        ]
        == "150.25"
    )
    assert customer.delete(f"/api/v1/cart/items/{item_id}/").json()["total"] == "0.00"
    customer.post("/api/v1/cart/items/", payload, format="json")
    assert customer.delete("/api/v1/cart/clear/").json()["items"] == []


@pytest.mark.parametrize("quantity", [0, -1, 101, 1.5, True, "2", None])
def test_invalid_quantities(customer, variant, quantity):
    response = customer.post(
        "/api/v1/cart/items/", {"variant": str(variant.pk), "quantity": quantity}, format="json"
    )
    assert response.status_code == 400
    assert not CartItem.objects.exists()


def test_anonymous_cart_isolated_and_adopted(api, user, variant):
    cart = api.get("/api/v1/cart/")
    token = cart["X-Cart-Token"]
    response = api.post(
        "/api/v1/cart/items/",
        {"variant": str(variant.pk), "quantity": 1},
        format="json",
        HTTP_X_CART_TOKEN=token,
    )
    assert len(response.json()["items"]) == 1
    assert api.get("/api/v1/cart/").json()["items"] == []
    assert api.get("/api/v1/cart/", HTTP_X_CART_TOKEN=token + "bad").status_code == 400
    api.force_authenticate(user)
    assert len(api.get("/api/v1/cart/", HTTP_X_CART_TOKEN=token).json()["items"]) == 1
    api.force_authenticate(None)
    assert api.get("/api/v1/cart/", HTTP_X_CART_TOKEN=token).status_code == 404


def test_item_ownership(customer, other_user, filled_cart):
    item_id = filled_cart["items"][0]["id"]
    customer.force_authenticate(other_user)
    assert (
        customer.patch(f"/api/v1/cart/items/{item_id}/", {"quantity": 1}, format="json").status_code
        == 404
    )
    assert customer.delete(f"/api/v1/cart/items/{item_id}/").status_code == 404


def test_combined_quantity_limit_and_inactive_variant(customer, variant):
    payload = {"variant": str(variant.pk), "quantity": 100}
    assert customer.post("/api/v1/cart/items/", payload, format="json").status_code == 201
    assert customer.post("/api/v1/cart/items/", payload, format="json").status_code == 400
    variant.is_active = False
    variant.save()
    assert (
        customer.post("/api/v1/cart/items/", {**payload, "quantity": 1}, format="json").status_code
        == 400
    )
