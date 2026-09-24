from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from inicio.constants import STATUS_PREVISTO
from inicio.duplicar import duplicar_objeto
from inicio.filtros import (
    MesPadraoMixin,
    RedirectFiltrosMixin,
    ano_request,
    aplicar_busca_status,
    mes_request,
    redirect_filtrado,
    redirect_mes_padrao,
    url_filtrada,
)
from inicio.forms import ReceitaForm
from inicio.models import Receita
from inicio.recorrencia import repetir_do_request, repetir_proximos, view_gerar_recorrentes
from inicio.servicos import contas_em_aberto, resumo_ano
from inicio.status import aplicar_status_receita, json_erro, json_status


def _apos_salvar(form, obj, request, mensagem):
    messages.success(request, mensagem)
    n = form.cleaned_data.get('repetir_meses') or 0
    if n:
        criados = repetir_proximos(obj, n)
        if criados:
            messages.success(request, f'{criados} cópia(s) criada(s) nos meses seguintes.')


def dashboard(request):
    ano = ano_request(request)
    resumo = resumo_ano(ano)
    abertos = contas_em_aberto(ano)
    dados_grafico = {
        'labels': [item['nome'][:3] for item in resumo['meses']],
        'receitas': [float(item['receita_total']) for item in resumo['meses']],
        'despesas': [float(item['despesa_total']) for item in resumo['meses']],
        'composicao_labels': [cat['nome'] for cat in resumo['categorias'].values()],
        'composicao_valores': [float(cat['total']) for cat in resumo['categorias'].values()],
    }
    return render(request, 'inicio/dashboard.html', {
        'ano': ano,
        'resumo': resumo,
        'abertos': abertos[:12],
        'abertos_total': len(abertos),
        'abertos_valor': sum((item['valor'] for item in abertos), 0),
        'dados_grafico': dados_grafico,
    })


def contas_a_pagar(request):
    redirecionar = redirect_mes_padrao(request)
    if redirecionar:
        return redirecionar
    ano = ano_request(request)
    mes = mes_request(request)
    abertos = contas_em_aberto(ano, mes)
    return render(request, 'inicio/contas_abertas.html', {
        'ano': ano,
        'mes_filtro': mes,
        'abertos': abertos,
        'abertos_total': len(abertos),
        'abertos_valor': sum((item['valor'] for item in abertos), 0),
    })


class ReceitaListView(MesPadraoMixin, ListView):
    model = Receita
    template_name = 'inicio/receitas_lista.html'
    context_object_name = 'receitas'

    def get_queryset(self):
        qs = Receita.objects.filter(ano=ano_request(self.request))
        return aplicar_busca_status(qs, self.request, ('fonte', 'observacao'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = context['receitas']
        context['ano'] = ano_request(self.request)
        context['total'] = sum((r.valor for r in qs), 0)
        context['a_receber'] = qs.filter(status=STATUS_PREVISTO).aggregate(s=Sum('valor'))['s'] or 0
        return context


class ReceitaCreateView(RedirectFiltrosMixin, CreateView):
    model = Receita
    form_class = ReceitaForm
    template_name = 'inicio/receita_form.html'
    lista_url = 'inicio:receitas'

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = ano_request(self.request)
        mes = mes_request(self.request)
        if mes:
            initial['mes'] = mes
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Receita cadastrada.')
        return response


class ReceitaUpdateView(RedirectFiltrosMixin, UpdateView):
    model = Receita
    form_class = ReceitaForm
    template_name = 'inicio/receita_form.html'
    lista_url = 'inicio:receitas'

    def form_valid(self, form):
        response = super().form_valid(form)
        _apos_salvar(form, self.object, self.request, 'Receita atualizada.')
        return response


def excluir_receita(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == 'POST':
        receita.delete()
        messages.success(request, 'Receita excluída.')
        return redirect_filtrado(request, 'inicio:receitas')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': receita,
        'titulo': 'Excluir receita',
        'voltar': url_filtrada(request, 'inicio:receitas'),
    })


@require_POST
def alternar_status_receita(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    try:
        aplicar_status_receita(receita, request.POST.get('status'))
    except ValidationError as exc:
        return json_erro(exc)
    receita.refresh_from_db()
    return json_status(receita)


@require_POST
def gerar_recorrentes_receitas(request):
    return view_gerar_recorrentes(request, Receita, 'inicio:receitas', 'receita(s)')


def duplicar_receita(request, pk):
    return duplicar_objeto(
        request,
        Receita,
        ReceitaForm,
        pk,
        'Duplicar receita',
        apos_salvar=lambda origem, novo, req: repetir_do_request(novo, req),
    )
