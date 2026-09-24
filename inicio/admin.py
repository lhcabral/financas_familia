from django.contrib import admin

from inicio.models import Ano, Receita


@admin.register(Ano)
class AnoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'ativo')
    list_editable = ('ativo',)
    list_filter = ('ativo',)
    search_fields = ('numero',)
    ordering = ['numero']


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ('fonte', 'mes', 'ano', 'valor', 'status', 'recorrente', 'observacao')
    list_filter = ('ano', 'mes', 'fonte', 'status', 'recorrente')
    search_fields = ('observacao',)
    list_editable = ('status',)
