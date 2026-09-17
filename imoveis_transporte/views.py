from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from imoveis_transporte.forms import ConsorcioForm, ParcelaConsorcioForm
from imoveis_transporte.models import Consorcio, ParcelaConsorcio
from inicio.constants import ANO_PADRAO, STATUS_ABERTO
from inicio.duplicar import duplicar_objeto
from inicio.status import aplicar_status, json_erro, json_status


def _ano(request):
    try:
        return int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        return ANO_PADRAO


class ParcelaListView(ListView):
    model = ParcelaConsorcio
    template_name = 'imoveis_transporte/lista.html'
    context_object_name = 'parcelas'

    def get_queryset(self):
        qs = ParcelaConsorcio.objects.filter(ano=_ano(self.request)).select_related('consorcio')
        mes = self.request.GET.get('mes')
        consorcio = self.request.GET.get('consorcio')
        if mes:
            qs = qs.filter(mes=int(mes))
        if consorcio:
            qs = qs.filter(consorcio_id=consorcio)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['parcelas']
        context['ano'] = _ano(self.request)
        context['consorcios'] = Consorcio.objects.all()
        context['total'] = qs.aggregate(s=Sum('valor'))['s'] or 0
        context['a_pagar'] = qs.filter(status=STATUS_ABERTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class ParcelaCreateView(CreateView):
    model = ParcelaConsorcio
    form_class = ParcelaConsorcioForm
    template_name = 'imoveis_transporte/form.html'
    success_url = reverse_lazy('imoveis_transporte:lista')

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = _ano(self.request)
        if self.request.GET.get('mes'):
            initial['mes'] = int(self.request.GET['mes'])
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Parcela cadastrada.')
        return super().form_valid(form)


class ParcelaUpdateView(UpdateView):
    model = ParcelaConsorcio
    form_class = ParcelaConsorcioForm
    template_name = 'imoveis_transporte/form.html'
    success_url = reverse_lazy('imoveis_transporte:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Parcela atualizada.')
        return super().form_valid(form)


def excluir_parcela(request, pk):
    parcela = get_object_or_404(ParcelaConsorcio, pk=pk)
    if request.method == 'POST':
        parcela.delete()
        messages.success(request, 'Parcela excluída.')
        return redirect('imoveis_transporte:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': parcela,
        'titulo': 'Excluir parcela',
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


def novo_consorcio(request):
    if request.method == 'POST':
        form = ConsorcioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consórcio cadastrado.')
            return redirect('imoveis_transporte:lista')
    else:
        form = ConsorcioForm()
    return render(request, 'imoveis_transporte/consorcio_form.html', {'form': form})


def duplicar_parcela(request, pk):
    return duplicar_objeto(
        request,
        ParcelaConsorcio,
        ParcelaConsorcioForm,
        pk,
        'Duplicar parcela',
    )
