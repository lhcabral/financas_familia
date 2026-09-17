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
    (STATUS_ABERTO, 'Aberto'),
    (STATUS_FECHADO, 'Fechado'),
    (STATUS_CARTAO, 'Cartão'),
]

STATUS_PAGAMENTO = [
    (STATUS_ABERTO, 'Aberto'),
    (STATUS_FECHADO, 'Fechado'),
]


def nome_mes(mes: int) -> str:
    return MESES_DICT.get(mes, str(mes))
