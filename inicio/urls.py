from django.urls import path

from . import views

app_name = 'inicio'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('receitas/', views.ReceitaListView.as_view(), name='receitas'),
    path('receitas/nova/', views.ReceitaCreateView.as_view(), name='receita_nova'),
    path('receitas/<int:pk>/editar/', views.ReceitaUpdateView.as_view(), name='receita_editar'),
    path('receitas/<int:pk>/excluir/', views.excluir_receita, name='receita_excluir'),
    path('receitas/<int:pk>/duplicar/', views.duplicar_receita, name='receita_duplicar'),
]
