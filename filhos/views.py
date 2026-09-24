from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from filhos.forms import DespesaFilhoForm, FilhoForm
from filhos.models import DespesaFilho, Filho
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


class DespesaFilhoListView(MesPadraoMixin, ListView):
    model = DespesaFilho
    template_name = 'filhos/lista.html'
    context_object_name = 'despesas'

    def get_queryset(self):
        qs = DespesaFilho.objects.filter(ano=ano_request(self.request)).select_related(
            'filho', 'item_fatura__fatura__cartao'
        )
        filho = self.request.GET.get('filho')
        if filho:
            qs = qs.filter(filho_id=filho)
        return aplicar_busca_status(qs, self.request, ('descricao', 'filho__nome'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['despesas']
        context['ano'] = ano_request(self.request)
        context['filhos'] = Filho.objects.all()
        context['total'] = qs.aggregate(s=Sum('valor'))['s'] or 0
        context['a_pagar'] = qs.filter(status=STATUS_ABERTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class DespesaFilhoCreateView(RedirectFiltrosMixin, CreateView):
    model = DespesaFilho
    form_class = DespesaFilhoForm
    template_name = 'filhos/form.html'
    lista_url = 'filhos:lista'

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = ano_request(self.request)
        mes = mes_request(self.request)
        if mes:
            initial['mes'] = mes
        if self.request.GET.get('filho'):
            initial['filho'] = self.request.GET['filho']
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Despesa do filho cadastrada.')
        return response


class DespesaFilhoUpdateView(RedirectFiltrosMixin, UpdateView):
    model = DespesaFilho
    form_class = DespesaFilhoForm
    template_name = 'filhos/form.html'
    lista_url = 'filhos:lista'

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Despesa do filho atualizada.')
        return response


def excluir_despesa(request, pk):
    despesa = get_object_or_404(DespesaFilho, pk=pk)
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, 'Despesa do filho excluída.')
        return redirect_filtrado(request, 'filhos:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': despesa,
        'titulo': 'Excluir despesa do filho',
        'voltar': url_filtrada(request, 'filhos:lista'),
    })


@require_POST
def alternar_status(request, pk):
    despesa = get_object_or_404(DespesaFilho, pk=pk)
    try:
        aplicar_status(
            despesa,
            request.POST.get('status'),
            cartao_id=request.POST.get('cartao_id'),
            descricao_item=f'{despesa.filho.nome} · {despesa.descricao}',
            valor=despesa.valor,
            ano=despesa.ano,
            mes=despesa.mes,
        )
    except ValidationError as exc:
        return json_erro(exc)
    despesa.refresh_from_db()
    return json_status(despesa)


@require_POST
def gerar_recorrentes_filhos(request):
    return view_gerar_recorrentes(request, DespesaFilho, 'filhos:lista', 'despesa(s)')


def cadastros_filhos(request):
    return render(request, 'filhos/cadastros.html', {
        'filhos': Filho.objects.all(),
        'voltar': url_filtrada(request, 'filhos:lista'),
    })


def novo_filho(request):
    if request.method == 'POST':
        form = FilhoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Filho cadastrado.')
            return redirect_filtrado(request, 'filhos:cadastros')
    else:
        form = FilhoForm()
    return render(request, 'filhos/filho_form.html', {
        'form': form,
        'voltar': url_filtrada(request, 'filhos:cadastros'),
    })


def editar_filho(request, pk):
    filho = get_object_or_404(Filho, pk=pk)
    if request.method == 'POST':
        form = FilhoForm(request.POST, instance=filho)
        if form.is_valid():
            form.save()
            messages.success(request, 'Filho atualizado.')
            return redirect_filtrado(request, 'filhos:cadastros')
    else:
        form = FilhoForm(instance=filho)
    return render(request, 'filhos/filho_form.html', {
        'form': form,
        'voltar': url_filtrada(request, 'filhos:cadastros'),
    })


def excluir_filho(request, pk):
    filho = get_object_or_404(Filho, pk=pk)
    qtd = filho.despesas.count()
    if request.method == 'POST':
        filho.delete()
        messages.success(request, 'Filho excluído.')
        return redirect_filtrado(request, 'filhos:cadastros')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': filho,
        'titulo': 'Excluir filho',
        'aviso': f'Isso também apaga {qtd} despesa(s) ligada(s) a este cadastro.' if qtd else '',
        'voltar': url_filtrada(request, 'filhos:cadastros'),
    })


def duplicar_despesa(request, pk):
    return duplicar_objeto(
        request,
        DespesaFilho,
        DespesaFilhoForm,
        pk,
        'Duplicar despesa do filho',
        apos_salvar=lambda origem, novo, req: repetir_do_request(novo, req),
    )
