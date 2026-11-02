from decimal import Decimal


def line_total(variant, quantity: int) -> Decimal:
    return (variant.price * quantity).quantize(Decimal("0.01"))


def cart_subtotal(items) -> Decimal:
    return sum((line_total(item.variant, item.quantity) for item in items), Decimal("0.00"))
