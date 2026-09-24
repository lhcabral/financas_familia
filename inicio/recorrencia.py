from django.contrib import messages

from inicio.constants import STATUS_ABERTO, STATUS_PREVISTO, nome_mes
from inicio.filtros import ano_request, mes_request, redirect_filtrado
from inicio.models import Receita


def avancar_mes(ano, mes, passos=1):
    total = (int(ano) * 12 + (int(mes) - 1)) + int(passos)
    return total // 12, (total % 12) + 1


def _filtros_iguais(obj, ano, mes):
    filtros = {'ano': ano, 'mes': mes}
    if hasattr(obj, 'filho_id'):
        filtros['filho_id'] = obj.filho_id
        filtros['descricao'] = obj.descricao
    elif hasattr(obj, 'consorcio_id'):
        filtros['consorcio_id'] = obj.consorcio_id
        if getattr(obj, 'recorrente', False):
            filtros['recorrente'] = True
        elif getattr(obj, 'numero_parcela', None):
            filtros['numero_parcela'] = obj.numero_parcela
    elif hasattr(obj, 'fonte'):
        filtros['fonte'] = obj.fonte
    elif hasattr(obj, 'descricao'):
        filtros['descricao'] = obj.descricao
    return filtros


def ja_existe(obj, ano, mes):
    return obj.__class__.objects.filter(**_filtros_iguais(obj, ano, mes)).exists()


def _rotulo_proxima(obj, numero):
    if obj.consorcio.total_parcelas:
        return f'{numero}/{obj.consorcio.total_parcelas}'
    if obj.rotulo_parcela and '/' in obj.rotulo_parcela:
        total = obj.rotulo_parcela.split('/', 1)[1]
        return f'{numero}/{total}'
    return str(numero)


def clonar_lancamento(obj, ano, mes, **extras):
    novo = obj.__class__.objects.get(pk=obj.pk)
    novo.pk = None
    novo.id = None
    novo.ano = ano
    novo.mes = mes
    if hasattr(novo, 'item_fatura_id'):
        novo.item_fatura = None
    if hasattr(novo, 'status'):
        novo.status = STATUS_PREVISTO if isinstance(obj, Receita) else STATUS_ABERTO
    for chave, valor in extras.items():
        setattr(novo, chave, valor)
    novo.save()
    return novo


def _extras_parcela(obj, incremento):
    if not hasattr(obj, 'numero_parcela'):
        return {}
    extras = {}
    if obj.numero_parcela:
        numero = obj.numero_parcela + incremento
        extras['numero_parcela'] = numero
        extras['rotulo_parcela'] = _rotulo_proxima(obj, numero)
    return extras


def repetir_proximos(obj, quantidade):
    criados = 0
    for passo in range(1, int(quantidade) + 1):
        ano, mes = avancar_mes(obj.ano, obj.mes, passo)
        if ja_existe(obj, ano, mes):
            continue
        clonar_lancamento(obj, ano, mes, **_extras_parcela(obj, passo))
        criados += 1
    return criados


def gerar_recorrentes(model, ano_origem, mes_origem):
    dest_ano, dest_mes = avancar_mes(ano_origem, mes_origem)
    qs = model.objects.filter(ano=ano_origem, mes=mes_origem, recorrente=True)
    if hasattr(model, 'filho'):
        qs = qs.select_related('filho')
    if hasattr(model, 'consorcio'):
        qs = qs.select_related('consorcio')
    criados = 0
    for obj in qs:
        if ja_existe(obj, dest_ano, dest_mes):
            continue
        clonar_lancamento(obj, dest_ano, dest_mes, **_extras_parcela(obj, 1))
        criados += 1
    return criados, dest_ano, dest_mes


def mensagem_recorrentes(criados, dest_ano, dest_mes, rotulo):
    mes = nome_mes(dest_mes)
    if criados:
        return f'{criados} {rotulo} gerado(s) para {mes}/{dest_ano}.'
    return f'Nenhum recorrente novo para {mes}/{dest_ano}.'


def repetir_do_request(obj, request, prefix='duplicar'):
    bruto = request.POST.get(f'{prefix}-repetir_meses') or request.POST.get('repetir_meses') or 0
    try:
        quantidade = int(bruto)
    except (TypeError, ValueError):
        quantidade = 0
    if quantidade:
        return repetir_proximos(obj, quantidade)
    return 0


def view_gerar_recorrentes(request, model, lista_url, rotulo):
    ano = ano_request(request)
    mes = mes_request(request)
    if not mes:
        messages.error(request, 'Selecione um mês para gerar os recorrentes do mês seguinte.')
        return redirect_filtrado(request, lista_url)
    criados, dest_ano, dest_mes = gerar_recorrentes(model, ano, mes)
    messages.success(request, mensagem_recorrentes(criados, dest_ano, dest_mes, rotulo))
    extras = {'ano': dest_ano, 'mes': dest_mes} if criados else None
    return redirect_filtrado(request, lista_url, extras)
