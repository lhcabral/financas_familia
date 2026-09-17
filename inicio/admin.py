from django.contrib import admin

from inicio.models import Receita


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ('fonte', 'mes', 'ano', 'valor', 'observacao')
    list_filter = ('ano', 'mes', 'fonte')
    search_fields = ('observacao',)
