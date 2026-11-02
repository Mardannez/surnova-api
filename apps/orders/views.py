from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.carts.views import CART_HEADER
from common.permissions import IsOwner

from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer
from .services.checkout_service import checkout


class CheckoutView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "checkout"

    @extend_schema(
        request=CheckoutSerializer,
        responses={201: OrderSerializer, 200: OrderSerializer},
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                str,
                OpenApiParameter.HEADER,
                required=True,
                description="UUID nuevo por intento lógico; reutilizar en reintentos de red.",
            ),
            CART_HEADER,
        ],
        examples=[
            OpenApiExample(
                "Entrega en Honduras",
                value={
                    "addresses": [
                        {
                            "address_type": "SHIPPING",
                            "full_name": "Ana López",
                            "phone": "+50499990000",
                            "address_line_1": "Colonia Centro, casa 10",
                            "city": "Tegucigalpa",
                            "state": "Francisco Morazán",
                            "country": "HN",
                        }
                    ],
                    "notes": "Llamar al llegar",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, created = checkout(
            user=request.user,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
            data=serializer.validated_data,
            cart_token=request.headers.get("X-Cart-Token"),
        )
        return Response(OrderSerializer(order).data, status=201 if created else 200)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [*APIView.permission_classes, IsOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "items", "addresses", "status_history"
        )
