from django.db import models


class IndicadorEconomico(models.Model):
    chave = models.CharField(max_length=30, unique=True)
    codigo_sgs = models.PositiveIntegerField(verbose_name='Código SGS')
    nome = models.CharField(max_length=80)
    valor = models.DecimalField(max_digits=10, decimal_places=4)
    data_referencia = models.DateField(verbose_name='Data de referência')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chave']
        verbose_name = 'Indicador econômico'
        verbose_name_plural = 'Indicadores econômicos'

    def __str__(self):
        return f'{self.nome}: {self.valor}'


class PerfilFinanceiro(models.Model):
    reserva_atual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Reserva atual',
        help_text='Quanto a família já tem guardado para emergências.',
    )
    meses_reserva = models.PositiveSmallIntegerField(
        default=6,
        verbose_name='Meses de reserva',
        help_text='Quantos meses de gastos a reserva deve cobrir.',
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil financeiro'
        verbose_name_plural = 'Perfil financeiro'

    def __str__(self):
        return 'Perfil financeiro da família'

    @classmethod
    def obter(cls):
        perfil, _ = cls.objects.get_or_create(pk=1)
        return perfil
