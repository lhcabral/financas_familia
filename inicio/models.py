from django.db import models

from inicio.constants import ANO_PADRAO, MESES


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

    class Meta:
        ordering = ['ano', 'mes', 'fonte']
        verbose_name = 'Receita'
        verbose_name_plural = 'Receitas'

    def __str__(self):
        return f'{self.get_fonte_display()} — {self.get_mes_display()}/{self.ano}'
