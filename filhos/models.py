from django.db import models

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_CHOICES
from inicio.vencimento import data_do_dia, situacao_vencimento


class Filho(models.Model):
    nome = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Filho'
        verbose_name_plural = 'Filhos'

    def __str__(self):
        return self.nome


class DespesaFilho(models.Model):
    filho = models.ForeignKey(Filho, on_delete=models.CASCADE, related_name='despesas')
    ano = models.PositiveIntegerField(default=ANO_PADRAO)
    mes = models.PositiveSmallIntegerField(choices=MESES)
    descricao = models.CharField(max_length=120)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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
        related_name='despesas_filhos',
    )

    class Meta:
        ordering = ['ano', 'mes', 'filho__nome', 'descricao']
        verbose_name = 'Despesa do filho'
        verbose_name_plural = 'Despesas dos filhos'

    def __str__(self):
        return f'{self.filho} — {self.descricao} ({self.get_mes_display()}/{self.ano})'

    @property
    def esta_aberto(self):
        return self.status == STATUS_ABERTO

    @property
    def data_vencimento(self):
        return data_do_dia(self.ano, self.mes, self.dia_vencimento)

    @property
    def situacao_vencimento(self):
        return situacao_vencimento(self.data_vencimento, self.esta_aberto)
