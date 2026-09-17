from django.urls import path

from . import views

app_name = 'filhos'

urlpatterns = [
    path('', views.DespesaFilhoListView.as_view(), name='lista'),
    path('nova/', views.DespesaFilhoCreateView.as_view(), name='nova'),
    path('filho/novo/', views.novo_filho, name='filho_novo'),
    path('<int:pk>/editar/', views.DespesaFilhoUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.excluir_despesa, name='excluir'),
    path('<int:pk>/status/', views.alternar_status, name='status'),
    path('<int:pk>/duplicar/', views.duplicar_despesa, name='duplicar'),
]
