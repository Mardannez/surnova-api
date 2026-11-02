from drf_spectacular.utils import OpenApiExample

LOGIN_EXAMPLES = [
    OpenApiExample(
        "Login por email",
        value={"email": "cliente@example.test", "password": "<tu contraseña>"},
        request_only=True,
    ),
    OpenApiExample(
        "Tokens emitidos",
        value={"access": "<JWT access>", "refresh": "<JWT refresh>"},
        response_only=True,
        status_codes=["200"],
    ),
]
REGISTER_EXAMPLES = [
    OpenApiExample(
        "Nuevo cliente",
        value={
            "email": "comprador@example.test",
            "password": "<contraseña de al menos 10 caracteres>",
            "first_name": "Ana",
            "last_name": "López",
            "phone": "+50499990000",
        },
        request_only=True,
    ),
]
CART_EXAMPLES = [
    OpenApiExample(
        "Añadir variante",
        value={"variant": "123e4567-e89b-42d3-a456-426614174000", "quantity": 2},
        request_only=True,
    ),
    OpenApiExample(
        "Totales del servidor",
        value={
            "id": "123e4567-e89b-42d3-a456-426614174001",
            "status": "ACTIVE",
            "items": [
                {
                    "id": "123e4567-e89b-42d3-a456-426614174002",
                    "variant": "123e4567-e89b-42d3-a456-426614174000",
                    "product_name": "Camiseta SURNOVA",
                    "variant_name": "Mediana / Azul",
                    "quantity": 2,
                    "unit_price": "350.00",
                    "line_total": "700.00",
                }
            ],
            "subtotal": "700.00",
            "total": "700.00",
            "updated_at": "2026-10-29T10:00:00-06:00",
        },
        response_only=True,
        status_codes=["201"],
    ),
]
