from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.examples import CART_EXAMPLES

from .models import Cart
from .serializers import AddItemSerializer, CartSerializer, UpdateItemSerializer
from .services import cart_service

CART_HEADER = OpenApiParameter(
    "X-Cart-Token",
    str,
    OpenApiParameter.HEADER,
    description="Token anónimo obtenido del header de respuesta; guardar y reenviar. Se puede adoptar al autenticar.",
)


def cart_response(cart, status=200):
    cart = Cart.objects.prefetch_related("items__variant__product").get(pk=cart.pk)
    response = Response(CartSerializer(cart).data, status=status)
    if cart.session_key:
        response["X-Cart-Token"] = cart_service.token_for(cart)
    return response


@extend_schema_view(get=extend_schema(responses=CartSerializer, parameters=[CART_HEADER]))
class CartView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def get(self, request):
        return cart_response(
            cart_service.get_cart(user=request.user, token=request.headers.get("X-Cart-Token"))
        )


class CartItemsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=AddItemSerializer,
        responses={201: CartSerializer},
        parameters=[CART_HEADER],
        examples=CART_EXAMPLES,
    )
    def post(self, request):
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return cart_response(
            cart_service.add_item(
                user=request.user,
                token=request.headers.get("X-Cart-Token"),
                variant_id=data["variant"],
                quantity=data["quantity"],
            ),
            status=201,
        )


class CartItemView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=UpdateItemSerializer, responses=CartSerializer, parameters=[CART_HEADER])
    def patch(self, request, id):
        serializer = UpdateItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return cart_response(
            cart_service.update_item(
                user=request.user,
                token=request.headers.get("X-Cart-Token"),
                item_id=id,
                quantity=serializer.validated_data["quantity"],
            )
        )

    @extend_schema(responses=CartSerializer, parameters=[CART_HEADER])
    def delete(self, request, id):
        return cart_response(
            cart_service.update_item(
                user=request.user,
                token=request.headers.get("X-Cart-Token"),
                item_id=id,
                delete=True,
            )
        )


class CartClearView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=CartSerializer, parameters=[CART_HEADER])
    def delete(self, request):
        return cart_response(
            cart_service.clear_cart(user=request.user, token=request.headers.get("X-Cart-Token"))
        )
