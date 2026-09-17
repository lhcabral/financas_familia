from django.db.utils import OperationalError, ProgrammingError

from cartoes.models import Cartao
from inicio.constants import ANO_PADRAO, MESES, STATUS_CHOICES, STATUS_PAGAMENTO


def financeiro(request):
    try:
        ano = int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        ano = ANO_PADRAO
    try:
        cartoes = list(Cartao.objects.values('id', 'nome'))
    except (OperationalError, ProgrammingError):
        cartoes = []
    return {
        'ano_selecionado': ano,
        'meses_nav': MESES,
        'anos_disponiveis': range(ANO_PADRAO - 1, ANO_PADRAO + 3),
        'status_choices': STATUS_CHOICES,
        'status_pagamento': STATUS_PAGAMENTO,
        'cartoes_json': cartoes,
    }
