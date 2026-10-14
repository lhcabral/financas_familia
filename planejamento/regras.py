from dataclasses import dataclass
from decimal import Decimal

from inicio.templatetags.financeiro import brl
from planejamento.calculos import desconto_equivalente, dinheiro

CRITICO = 'critico'
ATENCAO = 'atencao'
DICA = 'dica'
POSITIVO = 'positivo'

ORDEM_NIVEL = {CRITICO: 0, ATENCAO: 1, DICA: 2, POSITIVO: 3}
ROTULO_NIVEL = {CRITICO: 'Urgente', ATENCAO: 'Atenção', DICA: 'Dica', POSITIVO: 'Muito bem'}

LIMITE_CARTAO = 30
LIMITE_CARTAO_CRITICO = 40
LIMITE_NECESSIDADES = 50
META_POUPANCA = 20
POUPANCA_MINIMA = 10
LIMITE_PARCELAS = 30
PARCELAS_EXEMPLO = 10


@dataclass
class Sugestao:
    nivel: str
    titulo: str
    texto: str
    economia_mensal: Decimal | None = None

    @property
    def rotulo(self):
        return ROTULO_NIVEL[self.nivel]


def pct(valor, casas=1):
    return f'{valor:.{casas}f}%'.replace('.', ',')


def _por_mes(valor, meses):
    return dinheiro(valor / meses) if meses else dinheiro(valor)


def regra_contas_atrasadas(ctx):
    alertas = ctx['alertas']
    sugestoes = []
    if alertas['atrasadas']:
        quantidade = len(alertas['atrasadas'])
        tem_cartao = any(item['origem'] == 'Cartões' for item in alertas['atrasadas'])
        texto = (
            f'{quantidade} conta(s) vencida(s) somam {brl(alertas["valor_atrasado"])}. '
            f'Só de multa (2%) e juros (1% ao mês), o atraso já custa cerca de {brl(alertas["custo_atraso"])}.'
        )
        if tem_cartao:
            texto += ' Há fatura de cartão atrasada: os juros do rotativo são muito maiores, quite essa primeiro.'
        sugestoes.append(Sugestao(CRITICO, 'Pague as contas atrasadas', texto))
    if alertas['proximas']:
        sugestoes.append(Sugestao(
            DICA,
            'Contas vencendo nos próximos dias',
            f'{len(alertas["proximas"])} conta(s) vencem nos próximos 7 dias, '
            f'somando {brl(alertas["valor_proximas"])}. Pagar em dia evita multa e juros.',
        ))
    return sugestoes


def regra_saldo_e_poupanca(ctx):
    diag = ctx['diagnostico']
    receita, sobra, meses = diag['receita'], diag['sobra'], diag['quantidade_meses']
    if not receita:
        return []
    if sobra < 0:
        maior = diag['categorias'][0] if diag['categorias'] else None
        texto = f'Em {ctx["periodo_rotulo"]}, os gastos passaram a renda em {brl(-sobra)}.'
        if maior:
            texto += f' A maior categoria foi {maior["nome"]}, com {brl(maior["total"])} ({pct(maior["pct"])} da renda).'
        return [Sugestao(CRITICO, 'Gastos maiores que a renda', texto, _por_mes(-sobra, meses))]

    taxa = diag['taxa_poupanca']
    if taxa >= META_POUPANCA:
        return [Sugestao(
            POSITIVO,
            f'Vocês guardam {pct(taxa)} da renda',
            f'Está acima da meta de {META_POUPANCA}%. Garanta que essa sobra vá de fato para a reserva ou investimentos.',
        )]
    falta = receita * Decimal(META_POUPANCA) / 100 - sobra
    return [Sugestao(
        ATENCAO if taxa < POUPANCA_MINIMA else DICA,
        'Sobra pouco no fim do mês',
        f'Vocês guardam {pct(taxa)} da renda. O ideal é pelo menos {META_POUPANCA}%, '
        f'o que pede cortar cerca de {brl(_por_mes(falta, meses))} por mês.',
        _por_mes(falta, meses),
    )]


def regra_cartao(ctx):
    diag = ctx['diagnostico']
    taxa = diag['pct_cartao']
    if taxa is None or taxa <= LIMITE_CARTAO:
        return []
    excesso = diag['cartao'] - diag['receita'] * Decimal(LIMITE_CARTAO) / 100
    economia = _por_mes(excesso, diag['quantidade_meses'])
    return [Sugestao(
        CRITICO if taxa > LIMITE_CARTAO_CRITICO else ATENCAO,
        f'O cartão consome {pct(taxa)} da renda',
        f'O recomendado é até {LIMITE_CARTAO}%. Chegar a esse nível libera cerca de {brl(economia)} por mês. '
        'Revise assinaturas, compras pequenas repetidas e novos parcelamentos nas faturas.',
        economia,
    )]


def regra_necessidades(ctx):
    taxa = ctx['diagnostico']['pct_necessidades']
    if taxa is None or taxa <= LIMITE_NECESSIDADES:
        return []
    return [Sugestao(
        ATENCAO,
        f'Gastos fixos em {pct(taxa)} da renda',
        f'Casa, filhos, imóveis e carro passam dos {LIMITE_NECESSIDADES}% recomendados. '
        'Vale renegociar contratos (internet, seguros, planos) e rever o peso dos consórcios.',
    )]


def regra_reserva(ctx):
    reserva = ctx['reserva']
    if not reserva['meta']:
        return []
    if reserva['falta'] <= 0:
        texto = f'A reserva já cobre {reserva["meses_meta"]} meses de gastos.'
        if reserva['excedente'] > 0:
            texto += f' O que passa da meta ({brl(reserva["excedente"])}) pode ir para investimentos de prazo mais longo.'
        return [Sugestao(POSITIVO, 'Reserva de emergência completa', texto)]
    texto = f'Faltam {brl(reserva["falta"])} para cobrir {reserva["meses_meta"]} meses de gastos.'
    if reserva['meses_para_meta']:
        texto += (
            f' Guardando a sobra média de {brl(reserva["sobra_media"])} por mês num investimento atrelado ao CDI, '
            f'vocês chegam lá em cerca de {reserva["meses_para_meta"]} meses.'
        )
        nivel = DICA if (reserva['progresso'] or 0) >= 50 else ATENCAO
    else:
        texto += ' Hoje não sobra dinheiro no mês para montar a reserva: o primeiro passo é cortar gastos.'
        nivel = ATENCAO
    return [Sugestao(nivel, f'Reserva de emergência em {pct(reserva["progresso"] or 0, 0)}', texto)]


def regra_inflacao(ctx, limite=3):
    sugestoes = []
    for item in ctx['inflacao'][:limite]:
        sugestoes.append(Sugestao(
            ATENCAO,
            f'{item["descricao"]} subiu acima da inflação',
            f'Passou de {brl(item["valor_inicial"])} para {brl(item["valor_final"])} ({pct(item["variacao"])}) '
            f'entre {item["mes_inicial"]} e {item["mes_final"]}, enquanto a inflação no período foi de '
            f'{pct(item["inflacao"])}. Isso custa {brl(item["impacto_anual"])} a mais por ano. '
            'Vale revisar o consumo, negociar ou pesquisar outro fornecedor.',
            item['excesso_mensal'],
        ))
    return sugestoes


def regra_parcelas(ctx):
    compromissos = ctx['compromissos']
    renda = ctx['medias']['receita']
    sugestoes = []
    taxa = (float(compromissos['proximo_mes']) / float(renda) * 100) if renda else None
    if taxa is not None and taxa > LIMITE_PARCELAS:
        sugestoes.append(Sugestao(
            ATENCAO,
            f'Parcelas já levam {pct(taxa)} da renda do próximo mês',
            f'São {brl(compromissos["proximo_mes"])} em parcelas de cartão e consórcio já contratadas. '
            'Evite novos parcelamentos até essa fatia cair.',
        ))
    if compromissos['terminando_em_breve']:
        quantidade = len(compromissos['terminando_em_breve'])
        sugestoes.append(Sugestao(
            DICA,
            'Parcelas terminando em breve',
            f'Nos próximos 3 meses terminam {quantidade} parcelamento(s), liberando cerca de '
            f'{brl(compromissos["liberado_em_breve"])} por mês. Direcione esse valor para a reserva '
            'em vez de abrir novas parcelas.',
            compromissos['liberado_em_breve'],
        ))
    return sugestoes


def regra_poupanca_vs_cdi(ctx):
    linha = next((l for l in ctx['simulacao'] if l['meses'] == 12), None)
    if not linha or linha['cdi'] is None or linha['poupanca'] is None:
        return []
    diferenca = linha['cdi'] - linha['poupanca']
    if diferenca <= 0:
        return []
    return [Sugestao(
        DICA,
        'Prefira o CDI à poupança',
        f'Guardando {brl(ctx["aporte"])} por mês durante 12 meses, um investimento a 100% do CDI '
        f'(já descontado o IR) rende {brl(diferenca)} a mais que a poupança.',
    )]


def regra_desconto_a_vista(ctx):
    cdi = ctx['cdi']
    if cdi is None:
        return []
    desconto = desconto_equivalente(PARCELAS_EXEMPLO, cdi)
    return [Sugestao(
        DICA,
        'Quando vale pagar à vista',
        f'Com o CDI em {pct(float(cdi), 2)} ao ano, numa compra em {PARCELAS_EXEMPLO}x sem juros, '
        f'um desconto à vista acima de {pct(desconto)} compensa mais do que parcelar e deixar o dinheiro rendendo.',
    )]


REGRAS = (
    regra_contas_atrasadas,
    regra_saldo_e_poupanca,
    regra_cartao,
    regra_necessidades,
    regra_reserva,
    regra_inflacao,
    regra_parcelas,
    regra_poupanca_vs_cdi,
    regra_desconto_a_vista,
)


def gerar_sugestoes(ctx):
    sugestoes = [sugestao for regra in REGRAS for sugestao in regra(ctx)]
    sugestoes.sort(key=lambda s: ORDEM_NIVEL[s.nivel])
    return sugestoes
