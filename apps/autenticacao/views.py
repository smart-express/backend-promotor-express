from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .security import gerar_token_promotor
from .serializers import LoginPromotorRequestSerializer
from .services import SENHA_PADRAO_PROMOTOR, buscar_demonstrativo_por_cpf, buscar_promotor_por_cpf, limpar_cpf, obter_colunas_cadastros

class LoginPromotorView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Autenticação"], summary="Login do Promotor por CPF e retorno dos dados + demonstrativo", request=LoginPromotorRequestSerializer)
    def post(self, request):
        ser = LoginPromotorRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cpf_limpo = limpar_cpf(ser.validated_data["cpf"])
        if len(cpf_limpo) != 11 or ser.validated_data["senha"] != SENHA_PADRAO_PROMOTOR:
            return Response({"erro": "CPF ou senha inválidos."}, status=status.HTTP_401_UNAUTHORIZED)
        promotor = buscar_promotor_por_cpf(cpf_limpo)
        if not promotor:
            return Response({"erro": "Promotor não encontrado na base de cadastros."}, status=status.HTTP_401_UNAUTHORIZED)
        cols = obter_colunas_cadastros()
        token = gerar_token_promotor(str(promotor.get(cols["id"], "")), cpf_limpo, str(promotor.get(cols["nome"], "")))
        base_url = f"{request.scheme}://{request.get_host()}"
        return Response({
            "access_token": token,
            "token_type": "Bearer",
            "promotor": promotor,
            "demonstrativo": buscar_demonstrativo_por_cpf(cpf_limpo, base_url),
        })
