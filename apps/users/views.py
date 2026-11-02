from django.db import IntegrityError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.examples import LOGIN_EXAMPLES, REGISTER_EXAMPLES

from .serializers import LoginSerializer, LogoutSerializer, RegisterSerializer, UserSerializer


@extend_schema_view(
    post=extend_schema(
        examples=REGISTER_EXAMPLES,
        description="Registra un cliente sin privilegios administrativos. El email es único e ignora mayúsculas.",
    )
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def perform_create(self, serializer):
        try:
            serializer.save()
        except IntegrityError as exc:
            raise serializers.ValidationError({"email": "Este email ya está registrado."}) from exc


@extend_schema_view(
    post=extend_schema(
        examples=LOGIN_EXAMPLES,
        description="Emite access de 5 minutos y refresh de 7 días por defecto; ambos configurables.",
    )
)
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


@extend_schema_view(
    post=extend_schema(
        description="Rota el refresh y revoca el anterior. Guarda ambos tokens nuevos antes del próximo uso."
    )
)
class RefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token["user_id"]) != str(request.user.pk):
                raise InvalidToken("El refresh token no pertenece al usuario.")
            token.blacklist()
        except TokenError as exc:
            raise InvalidToken("Refresh token inválido.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
