from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Sum, Q
from django.urls import reverse

from cartoes.models import Fatura
from despesas_basicas.models import DespesaBasica
from filhos.models import DespesaFilho
from imoveis_transporte.models import ParcelaConsorcio
from inicio.constants import MESES, STATUS_ABERTO, STATUS_CARTAO, STATUS_PREVISTO
from inicio.models import Receita

ZERO = Decimal('0.00')


def _soma(queryset, campo='valor'):
    return queryset.aggregate(total=Sum(campo))['total'] or ZERO


def _url_lista(nome, ano, mes, extra=None):
    params = {'ano': ano, 'mes': mes}
    if extra:
        params.update(extra)
    return f'{reverse(nome)}?{urlencode(params)}'


def resumo_mes(ano, mes):
    desp = DespesaBasica.objects.filter(ano=ano, mes=mes)
    filhos = DespesaFilho.objects.filter(ano=ano, mes=mes)
    faturas = Fatura.objects.filter(ano=ano, mes=mes).prefetch_related('itens')
    parcelas = ParcelaConsorcio.objects.filter(ano=ano, mes=mes)
    receitas = Receita.objects.filter(ano=ano, mes=mes)

    tem_lancamentos = (
        desp.exists()
        or filhos.exists()
        or faturas.exists()
        or parcelas.exists()
        or receitas.exists()
    )

    cartoes_total = ZERO
    cartoes_pagar = ZERO
    for fatura in faturas:
        total = fatura.total or ZERO
        cartoes_total += total
        if fatura.status == STATUS_ABERTO:
            cartoes_pagar += total

    categorias = {
        'basicas': {
            'nome': 'Despesas da casa',
            'url_nome': 'despesas_basicas:lista',
            'total': _soma(desp.exclude(status=STATUS_CARTAO)),
            'a_pagar': _soma(desp.filter(status=STATUS_ABERTO)),
        },
        'filhos': {
            'nome': 'Filhos',
            'url_nome': 'filhos:lista',
            'total': _soma(filhos.exclude(status=STATUS_CARTAO)),
            'a_pagar': _soma(filhos.filter(status=STATUS_ABERTO)),
        },
        'cartoes': {
            'nome': 'Cartões',
            'url_nome': 'cartoes:lista',
            'total': cartoes_total,
            'a_pagar': cartoes_pagar,
        },
        'imoveis': {
            'nome': 'Imóveis e carro',
            'url_nome': 'imoveis_transporte:lista',
            'total': _soma(parcelas.exclude(status=STATUS_CARTAO)),
            'a_pagar': _soma(parcelas.filter(status=STATUS_ABERTO)),
        },
    }

    despesa_total = sum((item['total'] for item in categorias.values()), ZERO)
    a_pagar_total = sum((item['a_pagar'] for item in categorias.values()), ZERO)
    receita_total = _soma(receitas)
    a_receber = _soma(receitas.filter(status=STATUS_PREVISTO))
    saldo = receita_total - despesa_total

    return {
        'mes': mes,
        'nome': dict(MESES)[mes],
        'tem_lancamentos': tem_lancamentos,
        'categorias': categorias,
        'despesa_total': despesa_total,
        'a_pagar_total': a_pagar_total,
        'receita_total': receita_total,
        'a_receber': a_receber,
        'saldo': saldo,
        'receitas': receitas,
    }


def resumo_ano(ano):
    meses = [resumo_mes(ano, mes) for mes in range(1, 13)]
    meses_com_dados = [item for item in meses if item['tem_lancamentos']]
    receita = sum((item['receita_total'] for item in meses), ZERO)
    despesa = sum((item['despesa_total'] for item in meses), ZERO)
    a_pagar = sum((item['a_pagar_total'] for item in meses), ZERO)
    a_receber = sum((item['a_receber'] for item in meses), ZERO)
    categorias = {}
    if meses:
        for chave, cat in meses[0]['categorias'].items():
            categorias[chave] = {
                'nome': cat['nome'],
                'url_nome': cat['url_nome'],
                'total': sum((item['categorias'][chave]['total'] for item in meses), ZERO),
            }
    return {
        'meses': meses,
        'meses_com_dados': meses_com_dados,
        'receita_total': receita,
        'despesa_total': despesa,
        'a_pagar_total': a_pagar,
        'a_receber_total': a_receber,
        'saldo': receita - despesa,
        'categorias': categorias,
    }


def _item_aberto(origem, descricao, mes, valor, url_nome, ano, extra=None, data_venc=None, situacao=''):
    return {
        'origem': origem,
        'descricao': descricao,
        'mes': mes,
        'ano': ano,
        'valor': valor,
        'url': _url_lista(url_nome, ano, mes, extra),
        'data_vencimento': data_venc,
        'situacao': situacao or '',
    }


def contas_em_aberto(ano, mes=None):
    filtro = Q(ano=ano, status=STATUS_ABERTO)
    if mes:
        filtro &= Q(mes=mes)

    itens = []
    for desp in DespesaBasica.objects.filter(filtro):
        itens.append(_item_aberto(
            'Despesas da casa',
            desp.descricao,
            desp.mes,
            desp.valor,
            'despesas_basicas:lista',
            ano,
            data_venc=desp.data_vencimento,
            situacao=desp.situacao_vencimento,
        ))
    for desp in DespesaFilho.objects.filter(filtro).select_related('filho'):
        itens.append(_item_aberto(
            f'Filhos · {desp.filho.nome}',
            desp.descricao,
            desp.mes,
            desp.valor,
            'filhos:lista',
            ano,
            extra={'filho': desp.filho_id},
            data_venc=desp.data_vencimento,
            situacao=desp.situacao_vencimento,
        ))
    for fatura in Fatura.objects.filter(filtro).select_related('cartao'):
        total = fatura.total
        if total:
            itens.append(_item_aberto(
                'Cartões',
                fatura.cartao.nome,
                fatura.mes,
                total,
                'cartoes:lista',
                ano,
                extra={'cartao': fatura.cartao_id},
                data_venc=fatura.data_vencimento,
                situacao=fatura.situacao_vencimento,
            ))
    for parcela in ParcelaConsorcio.objects.filter(filtro).select_related('consorcio'):
        itens.append(_item_aberto(
            'Imóveis e transporte',
            parcela.consorcio.nome,
            parcela.mes,
            parcela.valor,
            'imoveis_transporte:lista',
            ano,
            extra={'consorcio': parcela.consorcio_id},
            data_venc=parcela.data_vencimento,
            situacao=parcela.situacao_vencimento,
        ))

    ordem_situacao = {'atrasada': 0, 'vence_hoje': 1}
    itens.sort(key=lambda item: (
        ordem_situacao.get(item['situacao'], 2),
        item['data_vencimento'] or date.max,
        item['mes'],
        item['origem'],
        item['descricao'],
    ))
    return itens
