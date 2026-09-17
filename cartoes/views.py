from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cartoes.forms import CartaoForm, FaturaForm, ItemFaturaForm
from cartoes.models import Cartao, Fatura, ItemFatura
from inicio.constants import ANO_PADRAO
from inicio.duplicar import PREFIXO, duplicar_objeto
from inicio.status import aplicar_status_fatura, json_erro, json_status


def _ano(request):
    try:
        return int(request.GET.get('ano', ANO_PADRAO))
    except (TypeError, ValueError):
        return ANO_PADRAO


class FaturaListView(ListView):
    model = Fatura
    template_name = 'cartoes/lista.html'
    context_object_name = 'faturas'

    def get_queryset(self):
        qs = (
            Fatura.objects.filter(ano=_ano(self.request))
            .select_related('cartao')
            .prefetch_related(Prefetch('itens', queryset=ItemFatura.objects.all()))
        )
        mes = self.request.GET.get('mes')
        cartao = self.request.GET.get('cartao')
        if mes:
            qs = qs.filter(mes=int(mes))
        if cartao:
            qs = qs.filter(cartao_id=cartao)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faturas = list(context['faturas'])
        context['ano'] = _ano(self.request)
        context['cartoes'] = Cartao.objects.all()
        context['total'] = sum((f.total for f in faturas), 0)
        context['a_pagar'] = sum((f.a_pagar for f in faturas), 0)
        return context


class FaturaCreateView(CreateView):
    model = Fatura
    form_class = FaturaForm
    template_name = 'cartoes/fatura_form.html'
    success_url = reverse_lazy('cartoes:lista')

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = _ano(self.request)
        if self.request.GET.get('mes'):
            initial['mes'] = int(self.request.GET['mes'])
        if self.request.GET.get('cartao'):
            initial['cartao'] = self.request.GET['cartao']
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Fatura cadastrada.')
        return super().form_valid(form)


class FaturaUpdateView(UpdateView):
    model = Fatura
    form_class = FaturaForm
    template_name = 'cartoes/fatura_form.html'
    success_url = reverse_lazy('cartoes:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Fatura atualizada.')
        return super().form_valid(form)


class FaturaDetailView(DetailView):
    model = Fatura
    template_name = 'cartoes/detalhe.html'
    context_object_name = 'fatura'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_item'] = ItemFaturaForm()
        context['total'] = self.object.total
        return context


def adicionar_item(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    if request.method == 'POST':
        form = ItemFaturaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.fatura = fatura
            item.save()
            messages.success(request, 'Item adicionado à fatura.')
        else:
            messages.error(request, 'Não foi possível adicionar o item. Confira os dados.')
    return redirect('cartoes:detalhe', pk=pk)


def excluir_item(request, pk):
    item = get_object_or_404(ItemFatura, pk=pk)
    fatura_id = item.fatura_id
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item excluído.')
    return redirect('cartoes:detalhe', pk=fatura_id)


def excluir_fatura(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    if request.method == 'POST':
        fatura.delete()
        messages.success(request, 'Fatura excluída.')
        return redirect('cartoes:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': fatura,
        'titulo': 'Excluir fatura',
    })


@require_POST
def alternar_status(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    try:
        aplicar_status_fatura(fatura, request.POST.get('status'))
    except ValidationError as exc:
        return json_erro(exc)
    fatura.refresh_from_db()
    return json_status(fatura)


def novo_cartao(request):
    if request.method == 'POST':
        form = CartaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cartão cadastrado.')
            return redirect('cartoes:lista')
    else:
        form = CartaoForm()
    return render(request, 'cartoes/cartao_form.html', {'form': form})


def _copiar_itens_fatura(origem, nova, request):
    if request.POST.get('copiar_itens'):
        for item in origem.itens.all():
            ItemFatura.objects.create(
                fatura=nova,
                descricao=item.descricao,
                valor=item.valor,
            )


def duplicar_fatura(request, pk):
    return duplicar_objeto(
        request,
        Fatura,
        FaturaForm,
        pk,
        'Duplicar fatura',
        extra_template='includes/copiar_itens_fatura.html',
        apos_salvar=_copiar_itens_fatura,
    )


def duplicar_item(request, pk):
    item = get_object_or_404(ItemFatura, pk=pk)
    if request.method == 'POST':
        form = ItemFaturaForm(request.POST, prefix=PREFIXO)
        if form.is_valid():
            novo = form.save(commit=False)
            novo.fatura = item.fatura
            novo.save()
            return JsonResponse({'ok': True})
        html = render_to_string(
            'includes/form_campos.html',
            {'form': form},
            request=request,
        )
        return JsonResponse({'ok': False, 'html': html}, status=400)
    form = ItemFaturaForm(
        prefix=PREFIXO,
        initial={'descricao': item.descricao, 'valor': item.valor},
    )
    html = render_to_string(
        'includes/form_campos.html',
        {'form': form},
        request=request,
    )
    return JsonResponse({'ok': True, 'html': html, 'titulo': 'Duplicar item'})
