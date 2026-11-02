import pytest
from django.test import override_settings

from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_register_login_me_refresh_logout(api):
    payload = {
        "email": "ANA@EXAMPLE.TEST",
        "password": "Excellent-secret-589!",
        "first_name": "Ana",
        "last_name": "López",
        "is_staff": True,
    }
    response = api.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == 201
    assert "password" not in response.json()
    user = User.objects.get(email="ana@example.test")
    assert not user.is_staff and user.check_password(payload["password"])
    tokens = api.post(
        "/api/v1/auth/login/",
        {"email": payload["email"], "password": payload["password"]},
        format="json",
    ).json()
    assert {"access", "refresh"} <= tokens.keys()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    me = api.patch("/api/v1/auth/me/", {"first_name": "Ana María", "is_staff": True}, format="json")
    assert me.status_code == 200 and me.json()["first_name"] == "Ana María"
    user.refresh_from_db()
    assert not user.is_staff
    rotated = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert rotated.status_code == 200
    assert (
        api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )
    refresh = rotated.json()["refresh"]
    assert api.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json").status_code == 204
    assert api.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json").status_code == 401


def test_registration_case_insensitive_and_password_validation(api, user):
    data = {"email": "ANA@EXAMPLE.TEST", "password": "123", "first_name": "A", "last_name": "B"}
    assert api.post("/api/v1/auth/register/", data, format="json").status_code == 400
    data["email"] = "nuevo@example.test"
    assert api.post("/api/v1/auth/register/", data, format="json").status_code == 400


@pytest.mark.parametrize("url", ["/api/v1/auth/me/", "/api/v1/orders/"])
def test_protected_endpoints(api, url):
    response = api.get(url)
    assert response.status_code == 401
    assert "error" in response.json()


def test_inactive_user_cannot_login(api, user):
    user.is_active = False
    user.save()
    assert (
        api.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "Testing-password-982!"},
            format="json",
        ).status_code
        == 401
    )


def test_cannot_logout_another_user_refresh(customer, other_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = str(RefreshToken.for_user(other_user))
    assert (
        customer.post("/api/v1/auth/logout/", {"refresh": token}, format="json").status_code == 401
    )
    assert str(RefreshToken(token)) == token


def test_login_rate_limit(api):
    from django.conf import settings
    from rest_framework.throttling import ScopedRateThrottle

    rates = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "login": "2/min"}
    with override_settings(
        REST_FRAMEWORK={**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}
    ):
        from unittest.mock import patch

        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, rates):
            data = {"email": "missing@example.test", "password": "wrong"}
            assert api.post("/api/v1/auth/login/", data, format="json").status_code == 401
            assert api.post("/api/v1/auth/login/", data, format="json").status_code == 401
            assert api.post("/api/v1/auth/login/", data, format="json").status_code == 429
