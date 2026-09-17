from django.db import models
from django.db.models import Sum

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_PAGAMENTO


class Cartao(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    titular = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Cartão'
        verbose_name_plural = 'Cartões'

    def __str__(self):
        return self.nome


class Fatura(models.Model):
    cartao = models.ForeignKey(Cartao, on_delete=models.CASCADE, related_name='faturas')
    ano = models.PositiveIntegerField(default=ANO_PADRAO)
    mes = models.PositiveSmallIntegerField(choices=MESES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_PAGAMENTO,
        default=STATUS_ABERTO,
    )

    class Meta:
        ordering = ['ano', 'mes', 'cartao__nome']
        unique_together = ('cartao', 'ano', 'mes')
        verbose_name = 'Fatura'
        verbose_name_plural = 'Faturas'

    def __str__(self):
        return f'{self.cartao} — {self.get_mes_display()}/{self.ano}'

    @property
    def total(self):
        return self.itens.aggregate(s=Sum('valor'))['s'] or 0

    @property
    def a_pagar(self):
        if self.status == STATUS_ABERTO:
            return self.total
        return 0


class ItemFatura(models.Model):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']
        verbose_name = 'Item da fatura'
        verbose_name_plural = 'Itens da fatura'

    def __str__(self):
        return f'{self.descricao} ({self.valor})'
