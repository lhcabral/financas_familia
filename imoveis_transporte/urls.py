from django.urls import path

from . import views

app_name = 'imoveis_transporte'

urlpatterns = [
    path('', views.ParcelaListView.as_view(), name='lista'),
    path('nova/', views.ParcelaCreateView.as_view(), name='nova'),
    path('gerar/', views.gerar_recorrentes_parcelas, name='gerar'),
    path('cadastros/', views.cadastros_consorcios, name='cadastros'),
    path('consorcio/novo/', views.novo_consorcio, name='consorcio_novo'),
    path('consorcio/<int:pk>/editar/', views.editar_consorcio, name='consorcio_editar'),
    path('consorcio/<int:pk>/excluir/', views.excluir_consorcio, name='consorcio_excluir'),
    path('<int:pk>/editar/', views.ParcelaUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.excluir_parcela, name='excluir'),
    path('<int:pk>/status/', views.alternar_status, name='status'),
    path('<int:pk>/duplicar/', views.duplicar_parcela, name='duplicar'),
]
