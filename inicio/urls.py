from django.urls import path

from . import views

app_name = 'inicio'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('contas-a-pagar/', views.contas_a_pagar, name='contas_a_pagar'),
    path('receitas/', views.ReceitaListView.as_view(), name='receitas'),
    path('receitas/nova/', views.ReceitaCreateView.as_view(), name='receita_nova'),
    path('receitas/gerar/', views.gerar_recorrentes_receitas, name='receitas_gerar'),
    path('receitas/<int:pk>/editar/', views.ReceitaUpdateView.as_view(), name='receita_editar'),
    path('receitas/<int:pk>/excluir/', views.excluir_receita, name='receita_excluir'),
    path('receitas/<int:pk>/status/', views.alternar_status_receita, name='receita_status'),
    path('receitas/<int:pk>/duplicar/', views.duplicar_receita, name='receita_duplicar'),
]
