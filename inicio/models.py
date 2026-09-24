from django.db import models

from inicio.constants import (
    ANO_PADRAO,
    MESES,
    STATUS_PREVISTO,
    STATUS_RECEBIDO,
    STATUS_RECEITA_CHOICES,
)
from inicio.vencimento import data_do_dia, situacao_vencimento


class Ano(models.Model):
    numero = models.PositiveIntegerField(unique=True, verbose_name='Ano')
    ativo = models.BooleanField(
        default=True,
        help_text='Se marcado, o ano aparece no seletor do sistema.',
    )

    class Meta:
        ordering = ['numero']
        verbose_name = 'Ano'
        verbose_name_plural = 'Anos'

    def __str__(self):
        return str(self.numero)


class Receita(models.Model):
    FONTE_SALARIO_ALINE = 'salario_aline'
    FONTE_SALARIO_LUIZ = 'salario_luiz'
    FONTE_MESADA_VOVO = 'mesada_vovo'
    FONTE_OUTROS = 'outros'

    FONTE_CHOICES = [
        (FONTE_SALARIO_ALINE, 'Salário Aline'),
        (FONTE_SALARIO_LUIZ, 'Salário Luiz'),
        (FONTE_MESADA_VOVO, 'Mesada Vovô'),
        (FONTE_OUTROS, 'Outros'),
    ]

    ano = models.PositiveIntegerField(default=ANO_PADRAO)
    mes = models.PositiveSmallIntegerField(choices=MESES)
    fonte = models.CharField(max_length=30, choices=FONTE_CHOICES)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    observacao = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_RECEITA_CHOICES,
        default=STATUS_RECEBIDO,
    )
    dia_vencimento = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Dia previsto',
        help_text='Dia do mês em que o valor deve entrar (1 a 31).',
    )
    recorrente = models.BooleanField(
        default=False,
        verbose_name='Lançamento recorrente',
        help_text='Permite gerar automaticamente no mês seguinte.',
    )

    class Meta:
        ordering = ['ano', 'mes', 'fonte']
        verbose_name = 'Receita'
        verbose_name_plural = 'Receitas'

    def __str__(self):
        return f'{self.get_fonte_display()} — {self.get_mes_display()}/{self.ano}'

    @property
    def data_vencimento(self):
        return data_do_dia(self.ano, self.mes, self.dia_vencimento)

    @property
    def situacao_vencimento(self):
        return situacao_vencimento(self.data_vencimento, self.status == STATUS_PREVISTO)
