from decimal import Decimal

from django.db.models import Sum, Q

from cartoes.models import Fatura
from despesas_basicas.models import DespesaBasica
from filhos.models import DespesaFilho
from imoveis_transporte.models import ParcelaConsorcio
from inicio.constants import MESES, STATUS_ABERTO, STATUS_CARTAO
from inicio.models import Receita

ZERO = Decimal('0.00')


def _soma(queryset, campo='valor'):
    return queryset.aggregate(total=Sum(campo))['total'] or ZERO


def resumo_mes(ano, mes):
    desp = DespesaBasica.objects.filter(ano=ano, mes=mes)
    filhos = DespesaFilho.objects.filter(ano=ano, mes=mes)
    faturas = Fatura.objects.filter(ano=ano, mes=mes).prefetch_related('itens')
    parcelas = ParcelaConsorcio.objects.filter(ano=ano, mes=mes)
    receitas = Receita.objects.filter(ano=ano, mes=mes)

    cartoes_total = ZERO
    cartoes_pagar = ZERO
    for fatura in faturas:
        total = fatura.total or ZERO
        cartoes_total += total
        if fatura.status == STATUS_ABERTO:
            cartoes_pagar += total

    categorias = {
        'basicas': {
            'nome': 'Desp. básicas',
            'total': _soma(desp.exclude(status=STATUS_CARTAO)),
            'a_pagar': _soma(desp.filter(status=STATUS_ABERTO)),
        },
        'filhos': {
            'nome': 'Filhos',
            'total': _soma(filhos.exclude(status=STATUS_CARTAO)),
            'a_pagar': _soma(filhos.filter(status=STATUS_ABERTO)),
        },
        'cartoes': {
            'nome': 'Cartões',
            'total': cartoes_total,
            'a_pagar': cartoes_pagar,
        },
        'imoveis': {
            'nome': 'Imóveis e carro',
            'total': _soma(parcelas.exclude(status=STATUS_CARTAO)),
            'a_pagar': _soma(parcelas.filter(status=STATUS_ABERTO)),
        },
    }

    despesa_total = sum((item['total'] for item in categorias.values()), ZERO)
    a_pagar_total = sum((item['a_pagar'] for item in categorias.values()), ZERO)
    receita_total = _soma(receitas)
    saldo = receita_total - despesa_total

    return {
        'mes': mes,
        'nome': dict(MESES)[mes],
        'categorias': categorias,
        'despesa_total': despesa_total,
        'a_pagar_total': a_pagar_total,
        'receita_total': receita_total,
        'saldo': saldo,
        'receitas': receitas,
    }


def resumo_ano(ano):
    meses = [resumo_mes(ano, mes) for mes in range(1, 13)]
    receita = sum((item['receita_total'] for item in meses), ZERO)
    despesa = sum((item['despesa_total'] for item in meses), ZERO)
    a_pagar = sum((item['a_pagar_total'] for item in meses), ZERO)
    return {
        'meses': meses,
        'receita_total': receita,
        'despesa_total': despesa,
        'a_pagar_total': a_pagar,
        'saldo': receita - despesa,
    }


def contas_em_aberto(ano, mes=None):
    filtro = Q(ano=ano, status=STATUS_ABERTO)
    if mes:
        filtro &= Q(mes=mes)

    itens = []
    for desp in DespesaBasica.objects.filter(filtro):
        itens.append({
            'origem': 'Despesas básicas',
            'descricao': desp.descricao,
            'mes': desp.mes,
            'valor': desp.valor,
            'url_nome': 'despesas_basicas:lista',
        })
    for desp in DespesaFilho.objects.filter(filtro).select_related('filho'):
        itens.append({
            'origem': f'Filhos · {desp.filho.nome}',
            'descricao': desp.descricao,
            'mes': desp.mes,
            'valor': desp.valor,
            'url_nome': 'filhos:lista',
        })
    for fatura in Fatura.objects.filter(filtro).select_related('cartao'):
        total = fatura.total
        if total:
            itens.append({
                'origem': 'Cartões',
                'descricao': fatura.cartao.nome,
                'mes': fatura.mes,
                'valor': total,
                'url_nome': 'cartoes:lista',
            })
    for parcela in ParcelaConsorcio.objects.filter(filtro).select_related('consorcio'):
        itens.append({
            'origem': 'Imóveis e transporte',
            'descricao': parcela.consorcio.nome,
            'mes': parcela.mes,
            'valor': parcela.valor,
            'url_nome': 'imoveis_transporte:lista',
        })
    itens.sort(key=lambda item: (item['mes'], item['origem'], item['descricao']))
    return itens
