from django.urls import path
from .views import CadastrosPaginadosView

urlpatterns = [
    path("", CadastrosPaginadosView.as_view(), name="cadastros-lista-paginada"),
]
