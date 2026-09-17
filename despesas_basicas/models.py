from django.db import models

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_CHOICES


class DespesaBasica(models.Model):
    ano = models.PositiveIntegerField(default=ANO_PADRAO)
    mes = models.PositiveSmallIntegerField(choices=MESES)
    descricao = models.CharField(max_length=120)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ABERTO,
    )
    item_fatura = models.ForeignKey(
        'cartoes.ItemFatura',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='despesas_basicas',
    )

    class Meta:
        ordering = ['ano', 'mes', 'descricao']
        verbose_name = 'Despesa básica'
        verbose_name_plural = 'Despesas básicas'

    def __str__(self):
        return f'{self.descricao} — {self.get_mes_display()}/{self.ano}'

    @property
    def esta_aberto(self):
        return self.status == STATUS_ABERTO
