from django.contrib import admin

from filhos.models import DespesaFilho, Filho


@admin.register(Filho)
class FilhoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(DespesaFilho)
class DespesaFilhoAdmin(admin.ModelAdmin):
    list_display = ('filho', 'descricao', 'mes', 'ano', 'valor', 'status', 'recorrente')
    list_filter = ('ano', 'mes', 'filho', 'status', 'recorrente')
    search_fields = ('descricao',)
    list_editable = ('status',)
