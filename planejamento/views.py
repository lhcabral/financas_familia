from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import render
from django.views.decorators.http import require_POST

from inicio.constants import nome_mes
from inicio.filtros import ano_request, mes_request, redirect_filtrado
from inicio.servicos import resumo_ano
from planejamento import banco_central, calculos
from planejamento.forms import PerfilFinanceiroForm
from planejamento.models import PerfilFinanceiro
from planejamento.regras import gerar_sugestoes

APORTE_PADRAO = Decimal('500.00')


def _rotulo_periodo(ano, mes, meses):
    if mes:
        return f'{nome_mes(mes).lower()} de {ano}'
    if not meses:
        return str(ano)
    if len(meses) == 1:
        return f'{meses[0]["nome"].lower()} de {ano}'
    return f'{meses[0]["nome"].lower()} a {meses[-1]["nome"].lower()} de {ano}'


def _aporte(request, medias):
    texto = (request.GET.get('aporte') or '').strip()
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    if texto:
        try:
            valor = Decimal(texto)
            if valor > 0:
                return calculos.dinheiro(valor)
        except InvalidOperation:
            pass
    if medias['sobra'] > 0:
        return medias['sobra']
    if medias['receita'] > 0:
        return calculos.dinheiro(medias['receita'] / 10)
    return APORTE_PADRAO


def painel(request):
    ano = ano_request(request)
    mes = mes_request(request)
    hoje = date.today()

    erros_bcb = banco_central.atualizar_indicadores()
    indicadores = banco_central.indicadores()
    cdi = banco_central.valor(indicadores, 'cdi')
    poupanca = banco_central.valor(indicadores, 'poupanca')
    ipca_12m = banco_central.valor(indicadores, 'ipca_12m')

    perfil = PerfilFinanceiro.obter()
    resumo = resumo_ano(ano)
    realizados = calculos.meses_realizados(resumo, ano, hoje)
    periodo_meses = [resumo['meses'][mes - 1]] if mes else realizados
    medias = calculos.medias_mensais(realizados)
    aporte = _aporte(request, medias)

    ctx = {
        'periodo_rotulo': _rotulo_periodo(ano, mes, periodo_meses),
        'diagnostico': calculos.diagnostico(calculos.agregar(periodo_meses)),
        'medias': medias,
        'reserva': calculos.reserva_emergencia(
            perfil.reserva_atual, perfil.meses_reserva, medias['despesa'], medias['sobra'], cdi,
        ),
        'aporte': aporte,
        'simulacao': calculos.simular_investimento(aporte, cdi, poupanca),
        'inflacao': calculos.contas_acima_inflacao(ano, ipca_12m, hoje),
        'compromissos': calculos.compromissos_futuros(hoje),
        'alertas': calculos.alertas_vencimento(hoje),
        'cdi': cdi,
    }
    sugestoes = gerar_sugestoes(ctx)

    renda = float(medias['receita'])
    dados_grafico = {
        'labels': [item['rotulo'] for item in ctx['compromissos']['serie']],
        'parcelas': [float(item['valor']) for item in ctx['compromissos']['serie']],
        'limite': [round(renda * 0.3, 2)] * len(ctx['compromissos']['serie']) if renda else [],
    }
    return render(request, 'planejamento/painel.html', {
        **ctx,
        'ano': ano,
        'mes_filtro': mes,
        'indicadores': indicadores,
        'indicadores_lista': list(indicadores.values()),
        'erros_bcb': erros_bcb,
        'sugestoes': sugestoes,
        'form_perfil': PerfilFinanceiroForm(instance=perfil),
        'dados_grafico': dados_grafico,
    })


@require_POST
def salvar_perfil(request):
    form = PerfilFinanceiroForm(request.POST, instance=PerfilFinanceiro.obter())
    if form.is_valid():
        form.save()
        messages.success(request, 'Reserva atualizada.')
    else:
        erros = '; '.join(e for lista in form.errors.values() for e in lista)
        messages.error(request, f'Não foi possível salvar: {erros}')
    return redirect_filtrado(request, 'planejamento:painel')


@require_POST
def atualizar_indicadores(request):
    erros = banco_central.atualizar_indicadores(forcar=True)
    if erros:
        messages.error(request, 'Falha ao atualizar indicadores: ' + ' '.join(erros))
    else:
        messages.success(request, 'Indicadores do Banco Central atualizados.')
    return redirect_filtrado(request, 'planejamento:painel')
