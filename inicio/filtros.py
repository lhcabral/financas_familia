from datetime import date
from urllib.parse import urlencode

from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse

from inicio.constants import ANO_PADRAO

FILTRO_KEYS = ('ano', 'mes', 'q', 'status', 'filho', 'cartao', 'consorcio')
MES_TODOS = 'todos'


def ano_request(request):
    origem = request.GET if request.method == 'GET' else request.GET or request.POST
    try:
        return int(origem.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        return ANO_PADRAO


def mes_request(request):
    valor = request.GET.get('mes') or request.POST.get('mes')
    if not valor or valor == MES_TODOS:
        return None
    try:
        mes = int(valor)
    except (TypeError, ValueError):
        return None
    return mes if 1 <= mes <= 12 else None


def mes_inicial(request):
    return mes_request(request)


def redirect_mes_padrao(request):
    if request.method != 'GET' or 'mes' in request.GET:
        return None
    params = request.GET.copy()
    params['mes'] = str(date.today().month)
    if 'ano' not in params:
        params['ano'] = str(ano_request(request))
    return redirect(f'{request.path}?{params.urlencode()}')


class MesPadraoMixin:
    def dispatch(self, request, *args, **kwargs):
        redirecionar = redirect_mes_padrao(request)
        if redirecionar:
            return redirecionar
        return super().dispatch(request, *args, **kwargs)


def filtros_request(request, extras=None):
    dados = {}
    for chave in FILTRO_KEYS:
        valor = request.GET.get(chave)
        if valor not in (None, ''):
            dados[chave] = valor
    if extras:
        for chave, valor in extras.items():
            if valor not in (None, ''):
                dados[chave] = valor
            else:
                dados.pop(chave, None)
    return dados


def url_filtrada(request, url_name, extras=None):
    url = reverse(url_name)
    query = urlencode(filtros_request(request, extras))
    return f'{url}?{query}' if query else url


def redirect_filtrado(request, url_name, extras=None):
    return redirect(url_filtrada(request, url_name, extras))


def aplicar_busca_status(qs, request, search_fields):
    mes = mes_request(request)
    if mes:
        qs = qs.filter(mes=mes)
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    termo = (request.GET.get('q') or '').strip()
    if termo and search_fields:
        condicao = Q()
        for campo in search_fields:
            condicao |= Q(**{f'{campo}__icontains': termo})
        qs = qs.filter(condicao)
    return qs


class RedirectFiltrosMixin:
    lista_url = None

    def get_success_url(self):
        return url_filtrada(self.request, self.lista_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['voltar'] = url_filtrada(self.request, self.lista_url)
        return context
