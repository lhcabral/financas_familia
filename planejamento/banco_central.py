"""Indicadores públicos do Banco Central (API SGS), salvos no banco para uso offline."""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils import timezone

from planejamento.models import IndicadorEconomico

URL_SERIE = (
    'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados'
    '?formato=json&dataInicial={inicio:%d/%m/%Y}&dataFinal={fim:%d/%m/%Y}'
)
JANELA_CONSULTA = timedelta(days=120)
TIMEOUT_AUTOMATICO = 4
TIMEOUT_MANUAL = 20
VALIDADE = timedelta(hours=24)
INTERVALO_ENTRE_TENTATIVAS = 60 * 30
CHAVE_CACHE_TENTATIVA = 'planejamento:bcb_tentativa'

SERIES = {
    'selic': {'codigo': 432, 'nome': 'Selic', 'unidade': 'ao ano'},
    'cdi': {'codigo': 4389, 'nome': 'CDI', 'unidade': 'ao ano'},
    'ipca_mes': {'codigo': 433, 'nome': 'IPCA do mês', 'unidade': 'inflação mensal'},
    'ipca_12m': {'codigo': 13522, 'nome': 'IPCA em 12 meses', 'unidade': 'acumulado'},
    'poupanca': {'codigo': 195, 'nome': 'Poupança', 'unidade': 'ao mês'},
}


class ErroBancoCentral(Exception):
    pass


def buscar_serie(codigo, timeout=TIMEOUT_MANUAL):
    """Retorna (data, valor) do ponto mais recente até hoje."""
    hoje = date.today()
    url = URL_SERIE.format(codigo=codigo, inicio=hoje - JANELA_CONSULTA, fim=hoje)
    requisicao = Request(url, headers={'Accept': 'application/json'})
    try:
        with urlopen(requisicao, timeout=timeout) as resposta:
            dados = json.load(resposta)
        pontos = [
            (datetime.strptime(ponto['data'], '%d/%m/%Y').date(), Decimal(ponto['valor']))
            for ponto in dados
        ]
    except HTTPError as exc:
        raise ErroBancoCentral(f'Banco Central recusou a série {codigo} ({exc.code}).') from exc
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ErroBancoCentral(f'Resposta inesperada da série {codigo}.') from exc
    if not pontos:
        raise ErroBancoCentral(f'Série {codigo} sem dados.')
    return max(pontos)


def _desatualizados():
    limite = timezone.now() - VALIDADE
    atuais = set(
        IndicadorEconomico.objects
        .filter(atualizado_em__gte=limite)
        .values_list('chave', flat=True)
    )
    return [chave for chave in SERIES if chave not in atuais]


def atualizar_indicadores(forcar=False):
    """Atualiza as séries vencidas. Retorna a lista de mensagens de erro."""
    chaves = list(SERIES) if forcar else _desatualizados()
    if not chaves:
        return []
    if not forcar and not cache.add(CHAVE_CACHE_TENTATIVA, True, INTERVALO_ENTRE_TENTATIVAS):
        return []

    timeout = TIMEOUT_MANUAL if forcar else TIMEOUT_AUTOMATICO
    erros = []
    for chave in chaves:
        serie = SERIES[chave]
        try:
            data_ref, valor = buscar_serie(serie['codigo'], timeout)
        except TimeoutError:
            erros.append(f'O Banco Central demorou para responder ({serie["nome"]}).')
            if forcar:
                continue
            break
        except OSError as exc:
            erros.append(f'Sem conexão com o Banco Central ({exc}).')
            break
        except ErroBancoCentral as exc:
            erros.append(str(exc))
            continue
        IndicadorEconomico.objects.update_or_create(
            chave=chave,
            defaults={
                'codigo_sgs': serie['codigo'],
                'nome': serie['nome'],
                'valor': valor,
                'data_referencia': data_ref,
            },
        )
    return erros


def indicadores():
    """Dicionário chave -> dados do indicador (ou None se nunca foi baixado)."""
    salvos = {item.chave: item for item in IndicadorEconomico.objects.all()}
    resultado = {}
    for chave, serie in SERIES.items():
        item = salvos.get(chave)
        resultado[chave] = {
            'chave': chave,
            'nome': serie['nome'],
            'unidade': serie['unidade'],
            'valor': item.valor if item else None,
            'data_referencia': item.data_referencia if item else None,
            'atualizado_em': item.atualizado_em if item else None,
        }
    return resultado


def valor(dados, chave):
    item = dados.get(chave) or {}
    return item.get('valor')
