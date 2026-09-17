from django.contrib import admin

from despesas_basicas.models import DespesaBasica


@admin.register(DespesaBasica)
class DespesaBasicaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'mes', 'ano', 'valor', 'status')
    list_filter = ('ano', 'mes', 'status', 'descricao')
    search_fields = ('descricao',)
    list_editable = ('status',)
