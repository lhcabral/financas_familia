from django.urls import path

from . import views

app_name = 'despesas_basicas'

urlpatterns = [
    path('', views.DespesaBasicaListView.as_view(), name='lista'),
    path('nova/', views.DespesaBasicaCreateView.as_view(), name='nova'),
    path('gerar/', views.gerar_recorrentes_despesas, name='gerar'),
    path('<int:pk>/editar/', views.DespesaBasicaUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.excluir_despesa, name='excluir'),
    path('<int:pk>/status/', views.alternar_status, name='status'),
    path('<int:pk>/duplicar/', views.duplicar_despesa, name='duplicar'),
]
