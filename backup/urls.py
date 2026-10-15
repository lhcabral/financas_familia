from django.urls import path

from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.painel, name='painel'),
    path('exportar/', views.exportar, name='exportar'),
    path('importar/', views.importar, name='importar'),
    path('agendamentos/novo/', views.agendamento_novo, name='agendamento_novo'),
    path('agendamentos/<int:pk>/editar/', views.agendamento_editar, name='agendamento_editar'),
    path('agendamentos/<int:pk>/excluir/', views.agendamento_excluir, name='agendamento_excluir'),
    path('agendamentos/<int:pk>/executar/', views.agendamento_executar, name='agendamento_executar'),
    path('arquivos/<str:nome>/', views.arquivo_baixar, name='arquivo_baixar'),
    path('arquivos/<str:nome>/excluir/', views.arquivo_excluir, name='arquivo_excluir'),
]
