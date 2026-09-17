from django.contrib import admin

from cartoes.models import Cartao, Fatura, ItemFatura


class ItemFaturaInline(admin.TabularInline):
    model = ItemFatura
    extra = 1


@admin.register(Cartao)
class CartaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'titular')
    search_fields = ('nome', 'titular')


@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ('cartao', 'mes', 'ano', 'status')
    list_filter = ('ano', 'mes', 'cartao', 'status')
    inlines = [ItemFaturaInline]
