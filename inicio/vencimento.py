from calendar import monthrange
from datetime import date


def data_do_dia(ano, mes, dia):
    if not ano or not mes or not dia:
        return None
    try:
        dia = int(dia)
    except (TypeError, ValueError):
        return None
    if dia < 1:
        return None
    ultimo = monthrange(int(ano), int(mes))[1]
    return date(int(ano), int(mes), min(dia, ultimo))


def situacao_vencimento(data, pendente):
    if not data or not pendente:
        return ''
    hoje = date.today()
    if data < hoje:
        return 'atrasada'
    if data == hoje:
        return 'vence_hoje'
    return ''
