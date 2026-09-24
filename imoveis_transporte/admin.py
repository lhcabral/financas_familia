from django.contrib import admin

from imoveis_transporte.models import Consorcio, ParcelaConsorcio


class ParcelaInline(admin.TabularInline):
    model = ParcelaConsorcio
    extra = 0


@admin.register(Consorcio)
class ConsorcioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'grupo', 'total_parcelas')
    search_fields = ('nome', 'grupo')
    inlines = [ParcelaInline]


@admin.register(ParcelaConsorcio)
class ParcelaConsorcioAdmin(admin.ModelAdmin):
    list_display = ('consorcio', 'mes', 'ano', 'rotulo_parcela', 'valor', 'status', 'recorrente')
    list_filter = ('ano', 'mes', 'consorcio', 'status', 'recorrente')
    list_editable = ('status',)
