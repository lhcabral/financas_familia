from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from filhos.forms import DespesaFilhoForm, FilhoForm
from filhos.models import DespesaFilho, Filho
from inicio.constants import ANO_PADRAO, STATUS_ABERTO
from inicio.duplicar import duplicar_objeto
from inicio.status import aplicar_status, json_erro, json_status


def _ano(request):
    try:
        return int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        return ANO_PADRAO


class DespesaFilhoListView(ListView):
    model = DespesaFilho
    template_name = 'filhos/lista.html'
    context_object_name = 'despesas'

    def get_queryset(self):
        qs = DespesaFilho.objects.filter(ano=_ano(self.request)).select_related('filho')
        mes = self.request.GET.get('mes')
        filho = self.request.GET.get('filho')
        if mes:
            qs = qs.filter(mes=int(mes))
        if filho:
            qs = qs.filter(filho_id=filho)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['despesas']
        context['ano'] = _ano(self.request)
        context['filhos'] = Filho.objects.all()
        context['total'] = qs.aggregate(s=Sum('valor'))['s'] or 0
        context['a_pagar'] = qs.filter(status=STATUS_ABERTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class DespesaFilhoCreateView(CreateView):
    model = DespesaFilho
    form_class = DespesaFilhoForm
    template_name = 'filhos/form.html'
    success_url = reverse_lazy('filhos:lista')

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = _ano(self.request)
        if self.request.GET.get('mes'):
            initial['mes'] = int(self.request.GET['mes'])
        if self.request.GET.get('filho'):
            initial['filho'] = self.request.GET['filho']
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Despesa do filho cadastrada.')
        return super().form_valid(form)


class DespesaFilhoUpdateView(UpdateView):
    model = DespesaFilho
    form_class = DespesaFilhoForm
    template_name = 'filhos/form.html'
    success_url = reverse_lazy('filhos:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Despesa do filho atualizada.')
        return super().form_valid(form)


def excluir_despesa(request, pk):
    despesa = get_object_or_404(DespesaFilho, pk=pk)
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, 'Despesa do filho excluída.')
        return redirect('filhos:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': despesa,
        'titulo': 'Excluir despesa do filho',
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


def novo_filho(request):
    if request.method == 'POST':
        form = FilhoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Filho cadastrado.')
            return redirect('filhos:lista')
    else:
        form = FilhoForm()
    return render(request, 'filhos/filho_form.html', {'form': form})


def duplicar_despesa(request, pk):
    return duplicar_objeto(
        request,
        DespesaFilho,
        DespesaFilhoForm,
        pk,
        'Duplicar despesa do filho',
    )
