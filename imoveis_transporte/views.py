from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from imoveis_transporte.forms import ConsorcioForm, ParcelaConsorcioForm
from imoveis_transporte.models import Consorcio, ParcelaConsorcio
from inicio.constants import STATUS_ABERTO
from inicio.duplicar import duplicar_objeto
from inicio.filtros import (
    MesPadraoMixin,
    RedirectFiltrosMixin,
    ano_request,
    aplicar_busca_status,
    mes_request,
    redirect_filtrado,
    url_filtrada,
)
from inicio.recorrencia import repetir_do_request, repetir_proximos, view_gerar_recorrentes
from inicio.status import aplicar_status, json_erro, json_status


def _apos_salvar(form, obj, request, mensagem):
    messages.success(request, mensagem)
    n = form.cleaned_data.get('repetir_meses') or 0
    if n:
        criados = repetir_proximos(obj, n)
        if criados:
            messages.success(request, f'{criados} cópia(s) criada(s) nos meses seguintes.')


class ParcelaListView(MesPadraoMixin, ListView):
    model = ParcelaConsorcio
    template_name = 'imoveis_transporte/lista.html'
    context_object_name = 'parcelas'

    def get_queryset(self):
        qs = ParcelaConsorcio.objects.filter(ano=ano_request(self.request)).select_related(
            'consorcio', 'item_fatura__fatura__cartao'
        )
        consorcio = self.request.GET.get('consorcio')
        if consorcio:
            qs = qs.filter(consorcio_id=consorcio)
        return aplicar_busca_status(qs, self.request, ('consorcio__nome', 'rotulo_parcela'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['parcelas']
        context['ano'] = ano_request(self.request)
        context['consorcios'] = Consorcio.objects.all()
        context['total'] = qs.aggregate(s=Sum('valor'))['s'] or 0
        context['a_pagar'] = qs.filter(status=STATUS_ABERTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class ParcelaCreateView(RedirectFiltrosMixin, CreateView):
    model = ParcelaConsorcio
    form_class = ParcelaConsorcioForm
    template_name = 'imoveis_transporte/form.html'
    lista_url = 'imoveis_transporte:lista'

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = ano_request(self.request)
        mes = mes_request(self.request)
        if mes:
            initial['mes'] = mes
        if self.request.GET.get('consorcio'):
            initial['consorcio'] = self.request.GET['consorcio']
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Parcela cadastrada.')
        return response


class ParcelaUpdateView(RedirectFiltrosMixin, UpdateView):
    model = ParcelaConsorcio
    form_class = ParcelaConsorcioForm
    template_name = 'imoveis_transporte/form.html'
    lista_url = 'imoveis_transporte:lista'

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Parcela atualizada.')
        return response


def excluir_parcela(request, pk):
    parcela = get_object_or_404(ParcelaConsorcio, pk=pk)
    if request.method == 'POST':
        parcela.delete()
        messages.success(request, 'Parcela excluída.')
        return redirect_filtrado(request, 'imoveis_transporte:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': parcela,
        'titulo': 'Excluir parcela',
        'voltar': url_filtrada(request, 'imoveis_transporte:lista'),
    })


@require_POST
def alternar_status(request, pk):
    parcela = get_object_or_404(ParcelaConsorcio, pk=pk)
    descricao = parcela.consorcio.nome
    if parcela.rotulo_parcela:
        descricao = f'{descricao} · {parcela.rotulo_parcela}'
    try:
        aplicar_status(
            parcela,
            request.POST.get('status'),
            cartao_id=request.POST.get('cartao_id'),
            descricao_item=descricao,
            valor=parcela.valor,
            ano=parcela.ano,
            mes=parcela.mes,
        )
    except ValidationError as exc:
        return json_erro(exc)
    parcela.refresh_from_db()
    return json_status(parcela)


@require_POST
def gerar_recorrentes_parcelas(request):
    return view_gerar_recorrentes(
        request, ParcelaConsorcio, 'imoveis_transporte:lista', 'parcela(s)',
    )


def cadastros_consorcios(request):
    return render(request, 'imoveis_transporte/cadastros.html', {
        'consorcios': Consorcio.objects.all(),
        'voltar': url_filtrada(request, 'imoveis_transporte:lista'),
    })


def novo_consorcio(request):
    if request.method == 'POST':
        form = ConsorcioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consórcio cadastrado.')
            return redirect_filtrado(request, 'imoveis_transporte:cadastros')
    else:
        form = ConsorcioForm()
    return render(request, 'imoveis_transporte/consorcio_form.html', {
        'form': form,
        'voltar': url_filtrada(request, 'imoveis_transporte:cadastros'),
    })


def editar_consorcio(request, pk):
    consorcio = get_object_or_404(Consorcio, pk=pk)
    if request.method == 'POST':
        form = ConsorcioForm(request.POST, instance=consorcio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consórcio atualizado.')
            return redirect_filtrado(request, 'imoveis_transporte:cadastros')
    else:
        form = ConsorcioForm(instance=consorcio)
    return render(request, 'imoveis_transporte/consorcio_form.html', {
        'form': form,
        'voltar': url_filtrada(request, 'imoveis_transporte:cadastros'),
    })


def excluir_consorcio(request, pk):
    consorcio = get_object_or_404(Consorcio, pk=pk)
    qtd = consorcio.parcelas.count()
    if request.method == 'POST':
        consorcio.delete()
        messages.success(request, 'Consórcio excluído.')
        return redirect_filtrado(request, 'imoveis_transporte:cadastros')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': consorcio,
        'titulo': 'Excluir consórcio',
        'aviso': f'Isso também apaga {qtd} parcela(s) deste consórcio.' if qtd else '',
        'voltar': url_filtrada(request, 'imoveis_transporte:cadastros'),
    })


def duplicar_parcela(request, pk):
    return duplicar_objeto(
        request,
        ParcelaConsorcio,
        ParcelaConsorcioForm,
        pk,
        'Duplicar parcela',
        apos_salvar=lambda origem, novo, req: repetir_do_request(novo, req),
    )
