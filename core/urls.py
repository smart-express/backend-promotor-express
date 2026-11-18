from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    return JsonResponse({"status": "online", "docs": "/api/docs/"})


urlpatterns = [
    path("", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    # Swagger / OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-legacy"),
    # Endpoints dos domínios
    path("api/auth/", include("apps.autenticacao.urls")),
    path("api/cadastros/", include("apps.cadastros.urls")),
]
