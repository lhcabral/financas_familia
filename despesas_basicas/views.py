from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from despesas_basicas.forms import DespesaBasicaForm
from despesas_basicas.models import DespesaBasica
from inicio.constants import ANO_PADRAO, STATUS_ABERTO
from inicio.duplicar import duplicar_objeto
from inicio.status import aplicar_status, json_erro, json_status


def _ano(request):
    try:
        return int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        return ANO_PADRAO


class DespesaBasicaListView(ListView):
    model = DespesaBasica
    template_name = 'despesas_basicas/lista.html'
    context_object_name = 'despesas'

    def get_queryset(self):
        qs = DespesaBasica.objects.filter(ano=_ano(self.request))
        mes = self.request.GET.get('mes')
        if mes:
            qs = qs.filter(mes=int(mes))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['despesas']
        context['ano'] = _ano(self.request)
        context['total'] = qs.aggregate(s=Sum('valor'))['s'] or 0
        context['a_pagar'] = qs.filter(status=STATUS_ABERTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class DespesaBasicaCreateView(CreateView):
    model = DespesaBasica
    form_class = DespesaBasicaForm
    template_name = 'despesas_basicas/form.html'
    success_url = reverse_lazy('despesas_basicas:lista')

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = _ano(self.request)
        if self.request.GET.get('mes'):
            initial['mes'] = int(self.request.GET['mes'])
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Despesa básica cadastrada.')
        return super().form_valid(form)


class DespesaBasicaUpdateView(UpdateView):
    model = DespesaBasica
    form_class = DespesaBasicaForm
    template_name = 'despesas_basicas/form.html'
    success_url = reverse_lazy('despesas_basicas:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Despesa básica atualizada.')
        return super().form_valid(form)


def excluir_despesa(request, pk):
    despesa = get_object_or_404(DespesaBasica, pk=pk)
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, 'Despesa básica excluída.')
        return redirect('despesas_basicas:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': despesa,
        'titulo': 'Excluir despesa básica',
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


def duplicar_despesa(request, pk):
    return duplicar_objeto(
        request,
        DespesaBasica,
        DespesaBasicaForm,
        pk,
        'Duplicar despesa básica',
    )
