from datetime import date

from django.db.utils import OperationalError, ProgrammingError

from cartoes.models import Cartao
from inicio.constants import (
    ANO_PADRAO,
    MESES,
    STATUS_CHOICES,
    STATUS_PAGAMENTO,
    STATUS_RECEITA_CHOICES,
)
from inicio.models import Ano


def _anos_disponiveis(ano_selecionado):
    try:
        anos = list(Ano.objects.filter(ativo=True).values_list('numero', flat=True))
    except (OperationalError, ProgrammingError):
        anos = []
    if not anos:
        anos = list(range(ANO_PADRAO - 1, ANO_PADRAO + 3))
    if ano_selecionado not in anos:
        anos = sorted(anos + [ano_selecionado])
    return anos


def financeiro(request):
    try:
        ano = int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        ano = ANO_PADRAO
    try:
        cartoes = list(Cartao.objects.values('id', 'nome'))
    except (OperationalError, ProgrammingError):
        cartoes = []
    hoje = date.today()
    return {
        'ano_selecionado': ano,
        'meses_nav': MESES,
        'anos_disponiveis': _anos_disponiveis(ano),
        'status_choices': STATUS_CHOICES,
        'status_pagamento': STATUS_PAGAMENTO,
        'status_receita': STATUS_RECEITA_CHOICES,
        'cartoes_json': cartoes,
        'hoje': hoje,
        'mes_atual': hoje.month,
        'ano_atual': hoje.year,
    }
