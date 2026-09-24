from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from despesas_basicas.forms import DespesaBasicaForm
from despesas_basicas.models import DespesaBasica
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


class DespesaBasicaListView(MesPadraoMixin, ListView):
    model = DespesaBasica
    template_name = 'despesas_basicas/lista.html'
    context_object_name = 'despesas'

    def get_queryset(self):
        qs = DespesaBasica.objects.filter(ano=ano_request(self.request)).select_related(
            'item_fatura__fatura__cartao'
        )
        return aplicar_busca_status(qs, self.request, ('descricao',))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['despesas']
        context['ano'] = ano_request(self.request)
        context['total'] = qs.aggregate(s=Sum('valor'))['s'] or 0
        context['a_pagar'] = qs.filter(status=STATUS_ABERTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class DespesaBasicaCreateView(RedirectFiltrosMixin, CreateView):
    model = DespesaBasica
    form_class = DespesaBasicaForm
    template_name = 'despesas_basicas/form.html'
    lista_url = 'despesas_basicas:lista'

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = ano_request(self.request)
        mes = mes_request(self.request)
        if mes:
            initial['mes'] = mes
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Despesa cadastrada.')
        return response


class DespesaBasicaUpdateView(RedirectFiltrosMixin, UpdateView):
    model = DespesaBasica
    form_class = DespesaBasicaForm
    template_name = 'despesas_basicas/form.html'
    lista_url = 'despesas_basicas:lista'

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Despesa atualizada.')
        return response


def excluir_despesa(request, pk):
    despesa = get_object_or_404(DespesaBasica, pk=pk)
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, 'Despesa excluída.')
        return redirect_filtrado(request, 'despesas_basicas:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': despesa,
        'titulo': 'Excluir despesa da casa',
        'voltar': url_filtrada(request, 'despesas_basicas:lista'),
    })


@require_POST
def alternar_status(request, pk):
    despesa = get_object_or_404(DespesaBasica, pk=pk)
    try:
        aplicar_status(
            despesa,
            request.POST.get('status'),
            cartao_id=request.POST.get('cartao_id'),
            descricao_item=despesa.descricao,
            valor=despesa.valor,
            ano=despesa.ano,
            mes=despesa.mes,
        )
    except ValidationError as exc:
        return json_erro(exc)
    despesa.refresh_from_db()
    return json_status(despesa)


@require_POST
def gerar_recorrentes_despesas(request):
    return view_gerar_recorrentes(request, DespesaBasica, 'despesas_basicas:lista', 'despesa(s)')


def duplicar_despesa(request, pk):
    return duplicar_objeto(
        request,
        DespesaBasica,
        DespesaBasicaForm,
        pk,
        'Duplicar despesa da casa',
        apos_salvar=lambda origem, novo, req: repetir_do_request(novo, req),
    )
