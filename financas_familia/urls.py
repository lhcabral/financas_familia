from django.contrib import admin
from django.urls import include, path

from inicio.acesso import EntrarView, SairView

admin.site.site_header = 'Finanças da família'
admin.site.site_title = 'Finanças da família'
admin.site.index_title = 'Administração'

urlpatterns = [
    path('entrar/', EntrarView.as_view(), name='entrar'),
    path('sair/', SairView.as_view(), name='sair'),
    path('admin/', admin.site.urls),
    path('', include('inicio.urls')),
    path('despesas-basicas/', include('despesas_basicas.urls')),
    path('filhos/', include('filhos.urls')),
    path('cartoes/', include('cartoes.urls')),
    path('imoveis-transporte/', include('imoveis_transporte.urls')),
]
