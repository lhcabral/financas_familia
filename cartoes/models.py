from django.db import models
from django.db.models import Sum

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_PAGAMENTO
from inicio.vencimento import data_do_dia, situacao_vencimento


class Cartao(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    titular = models.CharField(max_length=80, blank=True)
    dia_vencimento = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Dia de vencimento',
        help_text='Dia do mês em que a fatura vence (1 a 31).',
    )

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

    @property
    def quantidade_itens(self):
        return self.itens.count()

    @property
    def data_vencimento(self):
        return data_do_dia(self.ano, self.mes, self.cartao.dia_vencimento)

    @property
    def situacao_vencimento(self):
        return situacao_vencimento(self.data_vencimento, self.status == STATUS_ABERTO)


class ItemFatura(models.Model):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    quantidade_parcelas = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Qtd. parcelas',
        help_text='Total de parcelas da compra. Use 1 se for à vista.',
    )
    parcela_atual = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Parcela atual',
        help_text='Número desta parcela (ex.: 2 de 6).',
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'Item da fatura'
        verbose_name_plural = 'Itens da fatura'

    def __str__(self):
        return f'{self.descricao} ({self.valor})'

    @property
    def rotulo_parcela(self):
        total = self.quantidade_parcelas or 1
        atual = self.parcela_atual or 1
        if total <= 1:
            return ''
        return f'{atual}/{total}'

    @property
    def parcelas_restantes(self):
        total = self.quantidade_parcelas or 1
        atual = self.parcela_atual or 1
        return max(total - atual, 0)
