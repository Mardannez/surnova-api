from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La operación entra en conflicto con el estado actual."
    default_code = "conflict"


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {"code": getattr(exc, "default_code", "error"), "details": response.data}
        }
    return response


def json_bad_request(request, exception=None):
    from django.http import JsonResponse

    return JsonResponse(
        {"error": {"code": "bad_request", "details": "Solicitud inválida."}}, status=400
    )


def json_not_found(request, exception=None):
    from django.http import JsonResponse

    return JsonResponse(
        {"error": {"code": "not_found", "details": "Recurso no encontrado."}}, status=404
    )


def json_server_error(request):
    from django.http import JsonResponse

    return JsonResponse(
        {"error": {"code": "server_error", "details": "Error interno."}}, status=500
    )
