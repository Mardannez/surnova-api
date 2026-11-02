"""Document the common JSON error contract for every API operation."""

from copy import deepcopy


def order_status_choices():
    from apps.orders.models import Order

    return Order.Status.choices


def cart_status_choices():
    from apps.carts.models import Cart

    return Cart.Status.choices


def address_type_choices():
    from apps.orders.models import OrderAddress

    return OrderAddress.Type.choices


def add_error_responses(result, generator, request, public):
    schema = {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "details"],
                "properties": {
                    "code": {"type": "string"},
                    "details": {
                        "oneOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "array", "items": {}},
                            {"type": "string"},
                        ]
                    },
                },
            }
        },
    }
    result.setdefault("components", {}).setdefault("schemas", {})["ErrorEnvelope"] = schema
    errors = {
        "400": (
            "Datos inválidos o carrito vacío.",
            "invalid",
            {"quantity": ["Debe ser un entero entre 1 y 100."]},
        ),
        "401": (
            "Bearer token ausente, inválido o expirado.",
            "not_authenticated",
            {"detail": "Se requiere autenticación."},
        ),
        "403": ("Permisos insuficientes.", "permission_denied", {"detail": "No tienes permiso."}),
        "404": (
            "Recurso no encontrado o ajeno al usuario.",
            "not_found",
            {"detail": "No encontrado."},
        ),
        "409": (
            "Inventario insuficiente, idempotencia incompatible o transición inválida.",
            "conflict",
            {"detail": "Inventario insuficiente para completar la operación."},
        ),
        "429": (
            "Demasiadas solicitudes; respetar Retry-After.",
            "throttled",
            {"detail": "Límite de solicitudes excedido."},
        ),
        "500": ("Error interno sin trazas ni secretos.", "server_error", "Error interno."),
    }
    for path, path_item in result["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            for code, (description, error_code, details) in errors.items():
                operation.setdefault("responses", {}).setdefault(
                    code,
                    {
                        "description": description,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                                "example": {
                                    "error": {"code": error_code, "details": deepcopy(details)}
                                },
                            }
                        },
                    },
                )
    return result
