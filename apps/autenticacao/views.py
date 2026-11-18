from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginAdminRequestSerializer, LoginAdminResponseSerializer
from .services import autenticar_admin_e_carregar_cadastros


class LoginAdminView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Autenticação"],
        summary="Login de Administrador e retorno imediato de todos os Cadastros",
        request=LoginAdminRequestSerializer,
        responses={
            200: LoginAdminResponseSerializer,
            401: {"description": "Credenciais inválidas ou administrador inativo."},
        },
    )
    def post(self, request):
        serializer = LoginAdminRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resultado = autenticar_admin_e_carregar_cadastros(
            login_informado=serializer.validated_data["login"],
            senha_informada=serializer.validated_data["senha"],
        )

        if not resultado:
            return Response(
                {"erro": "Login ou senha inválidos, ou administrador inativo."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(resultado, status=status.HTTP_200_OK)
