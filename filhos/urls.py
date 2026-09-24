from django.urls import path

from . import views

app_name = 'filhos'

urlpatterns = [
    path('', views.DespesaFilhoListView.as_view(), name='lista'),
    path('nova/', views.DespesaFilhoCreateView.as_view(), name='nova'),
    path('gerar/', views.gerar_recorrentes_filhos, name='gerar'),
    path('cadastros/', views.cadastros_filhos, name='cadastros'),
    path('filho/novo/', views.novo_filho, name='filho_novo'),
    path('filho/<int:pk>/editar/', views.editar_filho, name='filho_editar'),
    path('filho/<int:pk>/excluir/', views.excluir_filho, name='filho_excluir'),
    path('<int:pk>/editar/', views.DespesaFilhoUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.excluir_despesa, name='excluir'),
    path('<int:pk>/status/', views.alternar_status, name='status'),
    path('<int:pk>/duplicar/', views.duplicar_despesa, name='duplicar'),
]
