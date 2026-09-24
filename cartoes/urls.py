from django.urls import path

from . import views

app_name = 'cartoes'

urlpatterns = [
    path('', views.FaturaListView.as_view(), name='lista'),
    path('novo/', views.FaturaCreateView.as_view(), name='nova'),
    path('cadastros/', views.cadastros_cartoes, name='cadastros'),
    path('cartao/novo/', views.novo_cartao, name='cartao_novo'),
    path('cartao/<int:pk>/editar/', views.editar_cartao, name='cartao_editar'),
    path('cartao/<int:pk>/excluir/', views.excluir_cartao, name='cartao_excluir'),
    path('<int:pk>/', views.FaturaDetailView.as_view(), name='detalhe'),
    path('<int:pk>/editar/', views.FaturaUpdateView.as_view(), name='editar'),
    path('<int:pk>/excluir/', views.excluir_fatura, name='excluir'),
    path('<int:pk>/status/', views.alternar_status, name='status'),
    path('<int:pk>/duplicar/', views.duplicar_fatura, name='duplicar'),
    path('<int:pk>/item/', views.adicionar_item, name='item_novo'),
    path('<int:pk>/importar/', views.importar_itens, name='item_importar'),
    path('item/<int:pk>/duplicar/', views.duplicar_item, name='item_duplicar'),
    path('item/<int:pk>/excluir/', views.excluir_item, name='item_excluir'),
]
