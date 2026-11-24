from datetime import datetime, timedelta, timezone
import jwt
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class UsuarioAutenticado(dict):
    @property
    def is_authenticated(self):
        return True

def gerar_token_promotor(cadastro_id: str, cpf_limpo: str, nome: str) -> str:
    agora = datetime.now(timezone.utc)
    payload = {"sub": str(cadastro_id), "cpf": cpf_limpo, "nome": nome, "iat": agora, "exp": agora + timedelta(hours=12)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

class PromotorJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        token = auth.split(" ", 1)[1].strip() if auth.startswith("Bearer ") else (request.query_params.get("token") or "").strip()
        if not token:
            return None
        try:
            return (UsuarioAutenticado(jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])), token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Sessão expirada.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Token inválido.")

class AdminKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        chave = request.headers.get("X-Admin-Key", "").strip()
        if not chave:
            return None
        if chave != settings.ADMIN_API_KEY:
            raise AuthenticationFailed("Chave administrativa inválida.")
        return (UsuarioAutenticado({"role": "admin"}), chave)

class PromotorJWTScheme(OpenApiAuthenticationExtension):
    target_class = "apps.autenticacao.security.PromotorJWTAuthentication"
    name = "PromotorBearerAuth"
    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}

class AdminKeyScheme(OpenApiAuthenticationExtension):
    target_class = "apps.autenticacao.security.AdminKeyAuthentication"
    name = "AdminApiKeyAuth"
    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "header", "name": "X-Admin-Key"}
