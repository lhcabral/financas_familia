import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from cartoes.models import ItemFatura
from despesas_basicas.models import DespesaBasica
from filhos.models import DespesaFilho
from imoveis_transporte.models import Consorcio
from inicio.constants import nome_mes
from inicio.servicos import ZERO, contas_em_aberto

CATEGORIAS_NECESSIDADE = ('basicas', 'filhos', 'imoveis')
CATEGORIAS_VARIAVEIS = ('cartoes',)
MULTA_ATRASO = Decimal('0.02')
JUROS_ATRASO_MES = Decimal('0.01')
HORIZONTES_SIMULACAO = (12, 24, 60)


def dinheiro(valor):
    return Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def percentual(parte, todo):
    if not todo:
        return None
    return float(parte) / float(todo) * 100


def indice_mes(ano, mes):
    return ano * 12 + (mes - 1)


def rotulo_indice(indice):
    ano, mes = divmod(indice, 12)
    return f'{nome_mes(mes + 1)[:3]}/{ano}'


def taxa_mensal(taxa_anual_pct):
    return (1 + float(taxa_anual_pct) / 100) ** (1 / 12) - 1


def aliquota_ir(meses):
    """Tabela regressiva do IR sobre renda fixa, pelo prazo da aplicação."""
    dias = meses * 30
    if dias <= 180:
        return 0.225
    if dias <= 360:
        return 0.20
    if dias <= 720:
        return 0.175
    return 0.15


# Período analisado ---------------------------------------------------------

def meses_realizados(resumo, ano, hoje=None):
    """Meses com lançamentos até o mês atual (meses futuros ainda estão incompletos)."""
    hoje = hoje or date.today()
    limite = indice_mes(hoje.year, hoje.month)
    meses = [m for m in resumo['meses_com_dados'] if indice_mes(ano, m['mes']) <= limite]
    return meses or resumo['meses_com_dados']


def agregar(meses):
    categorias = {}
    for mes in meses:
        for chave, cat in mes['categorias'].items():
            item = categorias.setdefault(chave, {'nome': cat['nome'], 'total': ZERO})
            item['total'] += cat['total']
    return {
        'quantidade_meses': len(meses),
        'receita_total': sum((m['receita_total'] for m in meses), ZERO),
        'despesa_total': sum((m['despesa_total'] for m in meses), ZERO),
        'categorias': categorias,
    }


def medias_mensais(meses):
    quantidade = len(meses)
    if not quantidade:
        return {'meses': 0, 'receita': ZERO, 'despesa': ZERO, 'sobra': ZERO}
    receita = sum((m['receita_total'] for m in meses), ZERO) / quantidade
    despesa = sum((m['despesa_total'] for m in meses), ZERO) / quantidade
    return {
        'meses': quantidade,
        'receita': dinheiro(receita),
        'despesa': dinheiro(despesa),
        'sobra': dinheiro(receita - despesa),
    }


# Diagnóstico -----------------------------------------------------------------

def _faixa(nome, descricao, valor, receita, meta, teto):
    pct = percentual(valor, receita)
    if pct is None:
        dentro = None
    else:
        dentro = pct <= meta if teto else pct >= meta
    return {
        'nome': nome,
        'descricao': descricao,
        'valor': valor,
        'pct': pct,
        'meta': meta,
        'teto': teto,
        'dentro': dentro,
        'largura': min(max(pct or 0, 0), 100),
    }


def diagnostico(periodo):
    receita = periodo['receita_total']
    despesa = periodo['despesa_total']
    sobra = receita - despesa
    cats = periodo['categorias']

    def total(chaves):
        return sum((cats[c]['total'] for c in chaves if c in cats), ZERO)

    necessidades = total(CATEGORIAS_NECESSIDADE)
    variaveis = total(CATEGORIAS_VARIAVEIS)
    cartao = total(('cartoes',))
    categorias = sorted(
        (
            {'chave': chave, 'nome': cat['nome'], 'total': cat['total'], 'pct': percentual(cat['total'], receita)}
            for chave, cat in cats.items()
        ),
        key=lambda item: item['total'],
        reverse=True,
    )
    return {
        'quantidade_meses': periodo['quantidade_meses'],
        'receita': receita,
        'despesa': despesa,
        'sobra': sobra,
        'taxa_poupanca': percentual(sobra, receita),
        'cartao': cartao,
        'pct_cartao': percentual(cartao, receita),
        'necessidades': necessidades,
        'pct_necessidades': percentual(necessidades, receita),
        'categorias': categorias,
        'regra_50_30_20': [
            _faixa('Necessidades', 'Casa, filhos, imóveis e carro', necessidades, receita, 50, teto=True),
            _faixa('Variáveis', 'Cartões de crédito', variaveis, receita, 30, teto=True),
            _faixa('Poupança', 'O que sobrou', max(sobra, ZERO), receita, 20, teto=False),
        ],
    }


# Investimentos e reserva -----------------------------------------------------

def projetar(aporte_mensal, taxa_mes, meses, inicial=0.0):
    saldo = inicial
    for _ in range(meses):
        saldo = saldo * (1 + taxa_mes) + aporte_mensal
    return saldo


def simular_investimento(aporte, cdi_anual, poupanca_mensal, horizontes=HORIZONTES_SIMULACAO):
    """Aporte no fim de cada mês. IR do CDI aproximado pela alíquota do prazo total."""
    aporte = float(aporte)
    linhas = []
    for meses in horizontes:
        investido = aporte * meses
        linha = {'meses': meses, 'investido': dinheiro(investido), 'cdi': None, 'poupanca': None}
        if cdi_anual is not None:
            bruto = projetar(aporte, taxa_mensal(cdi_anual), meses)
            liquido = investido + (bruto - investido) * (1 - aliquota_ir(meses))
            linha['cdi'] = dinheiro(liquido)
            linha['ganho_cdi'] = dinheiro(liquido - investido)
        if poupanca_mensal is not None:
            poupanca = projetar(aporte, float(poupanca_mensal) / 100, meses)
            linha['poupanca'] = dinheiro(poupanca)
            linha['ganho_poupanca'] = dinheiro(poupanca - investido)
        linhas.append(linha)
    return linhas


def _meses_ate_meta(inicial, aporte, taxa_mes, meta, limite=600):
    saldo = base = inicial
    for mes in range(1, limite + 1):
        saldo = saldo * (1 + taxa_mes) + aporte
        base += aporte
        liquido = base + (saldo - base) * (1 - aliquota_ir(mes))
        if liquido >= meta:
            return mes
    return None


def reserva_emergencia(reserva_atual, meses_meta, gasto_medio, sobra_media, cdi_anual):
    meta = dinheiro(gasto_medio * meses_meta)
    falta = max(meta - reserva_atual, ZERO)
    meses_para_meta = None
    if falta > 0 and sobra_media > 0:
        taxa = taxa_mensal(cdi_anual) if cdi_anual is not None else 0.0
        meses_para_meta = _meses_ate_meta(float(reserva_atual), float(sobra_media), taxa, float(meta))
    progresso = percentual(reserva_atual, meta)
    return {
        'atual': reserva_atual,
        'meses_meta': meses_meta,
        'gasto_medio': gasto_medio,
        'sobra_media': sobra_media,
        'meta': meta,
        'falta': falta,
        'excedente': max(reserva_atual - meta, ZERO) if meta else ZERO,
        'progresso': min(progresso, 100) if progresso is not None else None,
        'meses_para_meta': meses_para_meta,
    }


def desconto_equivalente(parcelas, cdi_anual):
    """Desconto à vista que empata com parcelar sem juros e deixar o dinheiro no CDI."""
    taxa = taxa_mensal(float(cdi_anual) * (1 - aliquota_ir(parcelas)))
    valor_presente = sum(1 / (1 + taxa) ** k for k in range(1, parcelas + 1)) / parcelas
    return (1 - valor_presente) * 100


# Contas acima da inflação ----------------------------------------------------

def _media(valores):
    return sum(valores, ZERO) / len(valores)


def contas_acima_inflacao(ano, ipca_12m, hoje=None, margem=1.0):
    """Despesas recorrentes (mesma descrição) cujo aumento passou da inflação do período."""
    if ipca_12m is None:
        return []
    hoje = hoje or date.today()
    limite = indice_mes(hoje.year, hoje.month)
    series = defaultdict(lambda: defaultdict(lambda: ZERO))
    nomes = {}

    def registrar(origem, descricao, ano_l, mes_l, valor):
        indice = indice_mes(ano_l, mes_l)
        if indice > limite or not valor:
            return
        chave = (origem, descricao.strip().lower())
        nomes.setdefault(chave, descricao.strip())
        series[chave][indice] += valor

    for d in DespesaBasica.objects.filter(ano__in=(ano - 1, ano)).values('descricao', 'ano', 'mes', 'valor'):
        registrar('Despesas da casa', d['descricao'], d['ano'], d['mes'], d['valor'])
    for d in DespesaFilho.objects.filter(ano__in=(ano - 1, ano)).values(
        'descricao', 'ano', 'mes', 'valor', 'filho__nome',
    ):
        registrar(f'Filhos · {d["filho__nome"]}', d['descricao'], d['ano'], d['mes'], d['valor'])

    resultado = []
    for chave, serie in series.items():
        indices = sorted(serie)
        intervalo = indices[-1] - indices[0]
        if len(indices) < 2 or intervalo < 2:
            continue
        valores = [serie[i] for i in indices]
        if len(valores) >= 4:
            inicial, final = _media(valores[:2]), _media(valores[-2:])
        else:
            inicial, final = valores[0], valores[-1]
        if inicial <= 0:
            continue
        variacao = (float(final) / float(inicial) - 1) * 100
        inflacao = ((1 + float(ipca_12m) / 100) ** (intervalo / 12) - 1) * 100
        if variacao <= inflacao + margem:
            continue
        excesso_mensal = dinheiro(float(final) - float(inicial) * (1 + inflacao / 100))
        if excesso_mensal < 1:
            continue
        resultado.append({
            'origem': chave[0],
            'descricao': nomes[chave],
            'mes_inicial': rotulo_indice(indices[0]),
            'mes_final': rotulo_indice(indices[-1]),
            'valor_inicial': dinheiro(inicial),
            'valor_final': dinheiro(final),
            'variacao': variacao,
            'inflacao': inflacao,
            'excesso_mensal': excesso_mensal,
            'impacto_anual': excesso_mensal * 12,
        })
    resultado.sort(key=lambda item: item['impacto_anual'], reverse=True)
    return resultado


# Compromissos futuros --------------------------------------------------------

def numeros_parcela(rotulo, numero):
    """'14,15,16,17/17' -> [14, 15, 16, 17]; sem rótulo usa o número da parcela."""
    if rotulo:
        numeros = [int(n) for n in re.findall(r'\d+', rotulo.split('/')[0])]
        if numeros:
            return numeros
    return [numero] if numero else []


def compromissos_futuros(hoje=None, meses_adiante=12):
    """Parcelas de cartão e consórcio a partir do próximo mês, sem contar a mesma compra duas vezes."""
    hoje = hoje or date.today()
    atual = indice_mes(hoje.year, hoje.month)
    agenda = defaultdict(lambda: ZERO)
    compromissos = []

    compras = {}
    for item in ItemFatura.objects.filter(quantidade_parcelas__gt=1).select_related('fatura__cartao'):
        inicio = indice_mes(item.fatura.ano, item.fatura.mes) - ((item.parcela_atual or 1) - 1)
        chave = (item.fatura.cartao_id, item.descricao.strip().lower(), item.quantidade_parcelas, item.valor, inicio)
        compras.setdefault(chave, item)
    for (_, _, total, valor, inicio), item in compras.items():
        futuras = [inicio + j for j in range(total) if inicio + j > atual]
        if not futuras:
            continue
        for indice in futuras:
            agenda[indice] += valor
        compromissos.append({
            'origem': f'Cartão · {item.fatura.cartao.nome}',
            'descricao': item.descricao,
            'valor_parcela': valor,
            'parcelas_restantes': len(futuras),
            'total_restante': valor * len(futuras),
            'termina_indice': futuras[-1],
        })

    for consorcio in Consorcio.objects.prefetch_related('parcelas'):
        parcelas = list(consorcio.parcelas.all())
        if not parcelas:
            continue
        futuras = {}
        for parcela in parcelas:
            indice = indice_mes(parcela.ano, parcela.mes)
            if indice > atual:
                futuras[indice] = futuras.get(indice, ZERO) + parcela.valor
        ultima = max(parcelas, key=lambda p: (
            max(numeros_parcela(p.rotulo_parcela, p.numero_parcela), default=0),
            indice_mes(p.ano, p.mes),
        ))
        numeros = numeros_parcela(ultima.rotulo_parcela, ultima.numero_parcela)
        if consorcio.total_parcelas and numeros:
            valor_unitario = ultima.valor / len(numeros)
            indice_ultima = indice_mes(ultima.ano, ultima.mes)
            for j in range(1, consorcio.total_parcelas - max(numeros) + 1):
                indice = indice_ultima + j
                if indice > atual:
                    futuras[indice] = futuras.get(indice, ZERO) + valor_unitario
        if not futuras:
            continue
        for indice, valor in futuras.items():
            agenda[indice] += valor
        ordenadas = sorted(futuras)
        compromissos.append({
            'origem': 'Consórcio',
            'descricao': str(consorcio),
            'valor_parcela': dinheiro(futuras[ordenadas[0]]),
            'parcelas_restantes': len(ordenadas),
            'total_restante': dinheiro(sum(futuras.values(), ZERO)),
            'termina_indice': ordenadas[-1],
        })

    for item in compromissos:
        item['termina'] = rotulo_indice(item['termina_indice'])
    compromissos.sort(key=lambda item: (item['termina_indice'], item['descricao']))
    serie = [
        {'indice': i, 'rotulo': rotulo_indice(i), 'valor': dinheiro(agenda.get(i, ZERO))}
        for i in range(atual + 1, atual + 1 + meses_adiante)
    ]
    terminando = [c for c in compromissos if c['termina_indice'] <= atual + 3]
    return {
        'serie': serie,
        'compromissos': compromissos,
        'total_restante': sum((c['total_restante'] for c in compromissos), ZERO),
        'proximo_mes': serie[0]['valor'] if serie else ZERO,
        'terminando_em_breve': terminando,
        'liberado_em_breve': sum((c['valor_parcela'] for c in terminando), ZERO),
    }


# Alertas ---------------------------------------------------------------------

def alertas_vencimento(hoje=None, dias_aviso=7):
    """Contas vencidas (com custo estimado de multa e juros) e as que vencem em breve."""
    hoje = hoje or date.today()
    itens = contas_em_aberto(hoje.year - 1) + contas_em_aberto(hoje.year)
    atrasadas, proximas = [], []
    for item in itens:
        vencimento = item['data_vencimento']
        if not vencimento:
            continue
        dias = (vencimento - hoje).days
        if dias < 0:
            custo = item['valor'] * (MULTA_ATRASO + JUROS_ATRASO_MES * Decimal(-dias) / 30)
            atrasadas.append({**item, 'dias_atraso': -dias, 'custo_estimado': dinheiro(custo)})
        elif dias <= dias_aviso:
            proximas.append({**item, 'dias_para_vencer': dias})
    return {
        'atrasadas': atrasadas,
        'proximas': proximas,
        'valor_atrasado': sum((i['valor'] for i in atrasadas), ZERO),
        'custo_atraso': sum((i['custo_estimado'] for i in atrasadas), ZERO),
        'valor_proximas': sum((i['valor'] for i in proximas), ZERO),
    }
