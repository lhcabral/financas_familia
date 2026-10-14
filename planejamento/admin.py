from django.contrib import admin

from planejamento.models import IndicadorEconomico, PerfilFinanceiro


@admin.register(IndicadorEconomico)
class IndicadorEconomicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_sgs', 'valor', 'data_referencia', 'atualizado_em')
    readonly_fields = ('atualizado_em',)


@admin.register(PerfilFinanceiro)
class PerfilFinanceiroAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'reserva_atual', 'meses_reserva', 'atualizado_em')
