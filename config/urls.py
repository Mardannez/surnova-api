from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.carts.views import CartClearView, CartItemsView, CartItemView, CartView
from apps.catalog.views import BrandViewSet, CategoryViewSet, ProductViewSet
from apps.orders.views import CheckoutView, OrderViewSet
from apps.users.views import LoginView, LogoutView, MeView, RefreshView, RegisterView

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("products", ProductViewSet, basename="product")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/auth/register/", RegisterView.as_view(), name="register"),
    path("api/v1/auth/login/", LoginView.as_view(), name="login"),
    path("api/v1/auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/v1/auth/me/", MeView.as_view(), name="me"),
    path("api/v1/cart/", CartView.as_view(), name="cart"),
    path("api/v1/cart/items/", CartItemsView.as_view(), name="cart-items"),
    path("api/v1/cart/items/<uuid:id>/", CartItemView.as_view(), name="cart-item"),
    path("api/v1/cart/clear/", CartClearView.as_view(), name="cart-clear"),
    path("api/v1/checkout/", CheckoutView.as_view(), name="checkout"),
    path("api/v1/", include(router.urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "common.exceptions.json_bad_request"
handler404 = "common.exceptions.json_not_found"
handler500 = "common.exceptions.json_server_error"
admin.site.site_header = "SURNOVA · Administración"
admin.site.site_title = "SURNOVA-API"
