import uuid

from django.core import signing
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.carts.models import Cart, CartItem
from apps.catalog.models import ProductVariant
from apps.users.models import User
from common.exceptions import Conflict

CART_SALT = "surnova.anonymous-cart.v1"


def session_from_token(token):
    try:
        value = signing.loads(token, salt=CART_SALT, max_age=30 * 86400)
        return str(uuid.UUID(value))
    except (signing.BadSignature, ValueError, TypeError) as exc:
        raise ValidationError({"cart_token": "Token de carrito inválido o expirado."}) from exc


def token_for(cart) -> str:
    return signing.dumps(cart.session_key, salt=CART_SALT) if cart.session_key else ""


@transaction.atomic
def get_cart(*, user, token=None) -> Cart:
    if user.is_authenticated:
        # Serializes first-cart creation, mutations, adoption and checkout for the same user.
        User.objects.select_for_update(no_key=True).get(pk=user.pk)
        active = (
            Cart.objects.select_for_update().filter(user=user, status=Cart.Status.ACTIVE).first()
        )
        if token:
            session_key = session_from_token(token)
            guest = (
                Cart.objects.select_for_update()
                .filter(session_key=session_key, user__isnull=True, status=Cart.Status.ACTIVE)
                .first()
            )
            if guest:
                if active and active.items.exists():
                    raise Conflict(
                        "Ya existe un carrito del usuario; vacíalo antes de adoptar el carrito anónimo."
                    )
                if active:
                    active.status = Cart.Status.CHECKED_OUT
                    active.save(update_fields=["status", "updated_at"])
                guest.user = user
                guest.session_key = None  # Revoke anonymous access immediately.
                guest.save(update_fields=["user", "session_key", "updated_at"])
                return guest
        if active:
            return active
        return Cart.objects.create(user=user)
    if token:
        key = session_from_token(token)
        cart = (
            Cart.objects.select_for_update()
            .filter(session_key=key, user__isnull=True, status=Cart.Status.ACTIVE)
            .first()
        )
        if cart is None:
            raise NotFound("Carrito no disponible.")
        return cart
    return Cart.objects.create(session_key=str(uuid.uuid4()))


def validate_quantity(quantity: int):
    if type(quantity) is not int or not 1 <= quantity <= 100:
        raise ValidationError({"quantity": "Debe ser un entero entre 1 y 100."})


def available_variant(variant_id):
    try:
        variant = ProductVariant.objects.select_related("product__category", "product__brand").get(
            pk=variant_id,
            is_active=True,
            product__is_active=True,
            product__category__is_active=True,
        )
    except ProductVariant.DoesNotExist as exc:
        raise ValidationError({"variant": "Variante no disponible."}) from exc
    if variant.product.brand_id and not variant.product.brand.is_active:
        raise ValidationError({"variant": "Variante no disponible."})
    return variant


@transaction.atomic
def add_item(*, user, token, variant_id, quantity: int):
    validate_quantity(quantity)
    cart = get_cart(user=user, token=token)
    variant = available_variant(variant_id)
    item = CartItem.objects.filter(cart=cart, variant=variant).first()
    if item:
        validate_quantity(item.quantity + quantity)
        item.quantity += quantity
        item.save(update_fields=["quantity", "updated_at"])
    else:
        if cart.items.count() >= 100:
            raise ValidationError("El carrito admite hasta 100 variantes.")
        CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
    cart.save(update_fields=["updated_at"])
    return cart


@transaction.atomic
def update_item(*, user, token, item_id, quantity=None, delete=False):
    cart = get_cart(user=user, token=token)
    try:
        item = CartItem.objects.get(pk=item_id, cart=cart)
    except CartItem.DoesNotExist as exc:
        raise NotFound("Artículo no encontrado.") from exc
    if delete:
        item.delete()
    else:
        validate_quantity(quantity)
        available_variant(item.variant_id)
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
    cart.save(update_fields=["updated_at"])
    return cart


@transaction.atomic
def clear_cart(*, user, token):
    cart = get_cart(user=user, token=token)
    cart.items.all().delete()
    cart.save(update_fields=["updated_at"])
    return cart
