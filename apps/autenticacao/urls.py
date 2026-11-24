from django.urls import path
from .views import ExcluirCadastrosView, ImportarCadastrosView, ListarCadastrosView, LoginPromotorView

urlpatterns = [
    path("login/", LoginPromotorView.as_view(), name="login-promotor"),
    path("cadastros/", ListarCadastrosView.as_view(), name="listar-cadastros"),
    path("cadastros/importar/", ImportarCadastrosView.as_view(), name="importar-cadastros"),
    path("cadastros/excluir/", ExcluirCadastrosView.as_view(), name="excluir-cadastros"),
]
