from django.urls import path

from . import views

app_name = 'planejamento'

urlpatterns = [
    path('', views.painel, name='painel'),
    path('reserva/', views.salvar_perfil, name='perfil'),
    path('indicadores/atualizar/', views.atualizar_indicadores, name='atualizar_indicadores'),
]
