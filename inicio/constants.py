ANO_PADRAO = 2026

MESES = [
    (1, 'Janeiro'),
    (2, 'Fevereiro'),
    (3, 'Março'),
    (4, 'Abril'),
    (5, 'Maio'),
    (6, 'Junho'),
    (7, 'Julho'),
    (8, 'Agosto'),
    (9, 'Setembro'),
    (10, 'Outubro'),
    (11, 'Novembro'),
    (12, 'Dezembro'),
]

MESES_DICT = dict(MESES)

STATUS_ABERTO = 'aberto'
STATUS_FECHADO = 'fechado'
STATUS_CARTAO = 'cartao'

STATUS_CHOICES = [
    (STATUS_ABERTO, 'A pagar'),
    (STATUS_FECHADO, 'Pago'),
    (STATUS_CARTAO, 'No cartão'),
]

STATUS_PAGAMENTO = [
    (STATUS_ABERTO, 'A pagar'),
    (STATUS_FECHADO, 'Paga'),
]

STATUS_PREVISTO = 'previsto'
STATUS_RECEBIDO = 'recebido'

STATUS_RECEITA_CHOICES = [
    (STATUS_PREVISTO, 'Previsto'),
    (STATUS_RECEBIDO, 'Recebido'),
]


def nome_mes(mes: int) -> str:
    return MESES_DICT.get(mes, str(mes))
