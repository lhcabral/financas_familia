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
        'previsto': 'status-aberto',
        'recebido': 'status-fechado',
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


@register.filter
def data_br(value):
    if not value:
        return '—'
    return value.strftime('%d/%m')


@register.filter
def get_item(dicionario, chave):
    if not dicionario:
        return ''
    return dicionario.get(chave, '')


@register.simple_tag
def qs(request, **kwargs):
    dados = request.GET.copy()
    for chave, valor in kwargs.items():
        if valor in (None, ''):
            dados.pop(chave, None)
        else:
            dados[chave] = valor
    return dados.urlencode()


@register.simple_tag
def qs_set(request, chave, valor=''):
    return qs(request, **{chave: valor})
