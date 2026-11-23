from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def health_check(request):
    return JsonResponse({"status": "online", "servico": "API Express", "docs": "/api/docs/"})

urlpatterns = [
    path("", health_check),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("apps.autenticacao.urls")),
    path("api/demonstrativos/", include("apps.demonstrativos.urls")),
]
