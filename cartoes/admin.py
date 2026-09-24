from django.contrib import admin

from cartoes.models import Cartao, Fatura, ItemFatura


class ItemFaturaInline(admin.TabularInline):
    model = ItemFatura
    extra = 1
    fields = ('descricao', 'valor', 'parcela_atual', 'quantidade_parcelas')


@admin.register(Cartao)
class CartaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'titular', 'dia_vencimento')
    search_fields = ('nome', 'titular')


@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ('cartao', 'mes', 'ano', 'status')
    list_filter = ('ano', 'mes', 'cartao', 'status')
    inlines = [ItemFaturaInline]
