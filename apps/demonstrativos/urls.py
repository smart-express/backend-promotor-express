from django.urls import path
from .views import ImportarLoteDemonstrativosView, LimparDemonstrativosView, LoteDemonstrativosListView, MeuDemonstrativoPdfView, MeuDemonstrativoView

urlpatterns = [
    path("meu/", MeuDemonstrativoView.as_view()),
    path("meu/pdf/", MeuDemonstrativoPdfView.as_view()),
    path("lote/", LoteDemonstrativosListView.as_view()),
    path("lote/importar/", ImportarLoteDemonstrativosView.as_view()),
    path("lote/limpar/", LimparDemonstrativosView.as_view()),
]
