from django.db import models

from inicio.constants import ANO_PADRAO, MESES, STATUS_ABERTO, STATUS_CHOICES


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
