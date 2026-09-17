from django.db import models

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_CHOICES


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
    item_fatura = models.ForeignKey(
        'cartoes.ItemFatura',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='parcelas_consorcio',
    )

    class Meta:
        ordering = ['ano', 'mes', 'consorcio__nome']
        unique_together = ('consorcio', 'ano', 'mes')
        verbose_name = 'Parcela de consórcio'
        verbose_name_plural = 'Parcelas de consórcio'

    def __str__(self):
        parcela = self.rotulo_parcela or self.numero_parcela or '-'
        return f'{self.consorcio} — {parcela} ({self.get_mes_display()}/{self.ano})'

    @property
    def esta_aberto(self):
        return self.status == STATUS_ABERTO
