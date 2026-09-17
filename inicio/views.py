from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from inicio.constants import ANO_PADRAO
from inicio.duplicar import duplicar_objeto
from inicio.forms import ReceitaForm
from inicio.models import Receita
from inicio.servicos import contas_em_aberto, resumo_ano


def _ano_request(request):
    try:
        return int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        return ANO_PADRAO


def dashboard(request):
    ano = _ano_request(request)
    resumo = resumo_ano(ano)
    abertos = contas_em_aberto(ano)
    return render(request, 'inicio/dashboard.html', {
        'ano': ano,
        'resumo': resumo,
        'abertos': abertos[:20],
        'abertos_total': len(abertos),
        'abertos_valor': sum((item['valor'] for item in abertos), 0),
    })


class ReceitaListView(ListView):
    model = Receita
    template_name = 'inicio/receitas_lista.html'
    context_object_name = 'receitas'

    def get_queryset(self):
        ano = _ano_request(self.request)
        qs = Receita.objects.filter(ano=ano)
        mes = self.request.GET.get('mes')
        if mes:
            qs = qs.filter(mes=int(mes))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ano'] = _ano_request(self.request)
        context['total'] = sum((r.valor for r in context['receitas']), 0)
        return context


class ReceitaCreateView(CreateView):
    model = Receita
    form_class = ReceitaForm
    template_name = 'inicio/receita_form.html'
    success_url = reverse_lazy('inicio:receitas')

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = _ano_request(self.request)
        if self.request.GET.get('mes'):
            initial['mes'] = int(self.request.GET['mes'])
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Receita cadastrada.')
        return super().form_valid(form)


class ReceitaUpdateView(UpdateView):
    model = Receita
    form_class = ReceitaForm
    template_name = 'inicio/receita_form.html'
    success_url = reverse_lazy('inicio:receitas')

    def form_valid(self, form):
        messages.success(self.request, 'Receita atualizada.')
        return super().form_valid(form)


def excluir_receita(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == 'POST':
        receita.delete()
        messages.success(request, 'Receita excluída.')
        return redirect('inicio:receitas')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': receita,
        'titulo': 'Excluir receita',
    })


def duplicar_receita(request, pk):
    return duplicar_objeto(
        request,
        Receita,
        ReceitaForm,
        pk,
        'Duplicar receita',
    )
