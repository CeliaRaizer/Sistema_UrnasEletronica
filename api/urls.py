from django.urls import path
from . import views, views_urnas as v

urlpatterns = [
    # autenticação
    path("login/", views.LoginAPIView.as_view(), name="api-login"),
    path("logout/", views.LogoutAPIView.as_view(), name="api-logout"),
    path("me/", views.MeAPIView.as_view(), name="api-me"),
    # campo (sem login)
    path("locais/", v.LocaisView.as_view()),
    path("urnas/consulta/", v.ConsultaUrnaView.as_view()),
    path("confirmar/", v.ConfirmarEntregaView.as_view()),
    path("ocorrencias/", v.OcorrenciaView.as_view()),
    # cartório (com login)
    path("locais/<int:pk>/", v.EditarLocalView.as_view()),
    path("locais/<int:pk>/impacto/", v.ImpactoLocalView.as_view()),
    path("locais/<int:pk>/excluir/", v.ExcluirLocalView.as_view()),
    path("rotas/<int:numero>/", v.EditarRotaView.as_view()),
    path("rotas/<int:numero>/impacto/", v.ImpactoRotaView.as_view()),
    path("rotas/<int:numero>/excluir/", v.ExcluirRotaView.as_view()),
    path("apagar-dados/", v.ApagarDadosView.as_view()),
    path("painel/", v.PainelView.as_view()),
    path("ocorrencias/lista/", v.OcorrenciasListaView.as_view()),
    path("importar/", v.ImportarPlanilhaView.as_view()),
    path("importar-locais/", v.ImportarLocaisView.as_view()),
    path("importar-presidentes/", v.ImportarPresidentesView.as_view()),
    path("secoes/", v.SecoesView.as_view()),
    path("urnas/associar/", v.AssociarUrnaView.as_view()),
]
