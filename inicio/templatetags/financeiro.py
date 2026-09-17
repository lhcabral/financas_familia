from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def brl(value):
    if value is None or value == '':
        return 'R$ 0,00'
    try:
        numero = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return 'R$ 0,00'
    formatado = f'{numero:,.2f}'
    return 'R$ ' + formatado.replace(',', 'X').replace('.', ',').replace('X', '.')


@register.filter
def status_classe(status):
    mapa = {
        'aberto': 'status-aberto',
        'fechado': 'status-fechado',
        'cartao': 'status-cartao',
    }
    return mapa.get(status, '')


@register.filter
def saldo_classe(valor):
    try:
        numero = Decimal(str(valor or 0))
    except (InvalidOperation, TypeError, ValueError):
        return 'saldo-zero'
    if numero > 0:
        return 'saldo-positivo'
    if numero < 0:
        return 'saldo-negativo'
    return 'saldo-zero'
