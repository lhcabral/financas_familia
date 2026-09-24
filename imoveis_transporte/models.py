from django.db import models

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_CHOICES
from inicio.vencimento import data_do_dia, situacao_vencimento


class Consorcio(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    grupo = models.CharField(max_length=80, blank=True)
    total_parcelas = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Consórcio'
        verbose_name_plural = 'Consórcios'

    def __str__(self):
        if self.grupo:
            return f'{self.nome} ({self.grupo})'
        return self.nome


class ParcelaConsorcio(models.Model):
    consorcio = models.ForeignKey(
        Consorcio,
        on_delete=models.CASCADE,
        related_name='parcelas',
    )
    ano = models.PositiveIntegerField(default=ANO_PADRAO)
    mes = models.PositiveSmallIntegerField(choices=MESES)
    numero_parcela = models.PositiveIntegerField(null=True, blank=True)
    rotulo_parcela = models.CharField(max_length=20, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ABERTO,
    )
    dia_vencimento = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Dia de vencimento',
        help_text='Dia do mês em que vence (1 a 31).',
    )
    recorrente = models.BooleanField(
        default=False,
        verbose_name='Lançamento recorrente',
        help_text='Permite gerar automaticamente no mês seguinte.',
    )
    item_fatura = models.ForeignKey(
        'cartoes.ItemFatura',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='parcelas_consorcio',
    )

    class Meta:
        ordering = ['ano', 'mes', 'consorcio__nome', 'numero_parcela', 'id']
        verbose_name = 'Parcela de consórcio'
        verbose_name_plural = 'Parcelas de consórcio'

    def __str__(self):
        parcela = self.rotulo_parcela or self.numero_parcela or '-'
        return f'{self.consorcio} — {parcela} ({self.get_mes_display()}/{self.ano})'

    @property
    def esta_aberto(self):
        return self.status == STATUS_ABERTO

    @property
    def data_vencimento(self):
        return data_do_dia(self.ano, self.mes, self.dia_vencimento)

    @property
    def situacao_vencimento(self):
        return situacao_vencimento(self.data_vencimento, self.esta_aberto)
