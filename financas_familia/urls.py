from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Finanças da família'
admin.site.site_title = 'Finanças da família'
admin.site.index_title = 'Administração'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inicio.urls')),
    path('despesas-basicas/', include('despesas_basicas.urls')),
    path('filhos/', include('filhos.urls')),
    path('cartoes/', include('cartoes.urls')),
    path('imoveis-transporte/', include('imoveis_transporte.urls')),
]
