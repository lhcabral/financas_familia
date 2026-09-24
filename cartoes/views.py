from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cartoes.forms import CartaoForm, FaturaForm, ImportarItensCSVForm, ItemFaturaForm
from cartoes.models import Cartao, Fatura, ItemFatura
from cartoes.servicos import importar_itens_arquivo, salvar_item_com_parcelas
from inicio.duplicar import PREFIXO, duplicar_objeto
from inicio.filtros import (
    MesPadraoMixin,
    RedirectFiltrosMixin,
    ano_request,
    aplicar_busca_status,
    mes_request,
    redirect_filtrado,
    url_filtrada,
)
from inicio.status import aplicar_status_fatura, json_erro, json_status


class FaturaListView(MesPadraoMixin, ListView):
    model = Fatura
    template_name = 'cartoes/lista.html'
    context_object_name = 'faturas'

    def get_queryset(self):
        qs = (
            Fatura.objects.filter(ano=ano_request(self.request))
            .select_related('cartao')
            .prefetch_related(Prefetch('itens', queryset=ItemFatura.objects.all()))
        )
        cartao = self.request.GET.get('cartao')
        if cartao:
            qs = qs.filter(cartao_id=cartao)
        return aplicar_busca_status(qs, self.request, ('cartao__nome', 'cartao__titular'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faturas = list(context['faturas'])
        context['ano'] = ano_request(self.request)
        context['cartoes'] = Cartao.objects.all()
        context['total'] = sum((f.total for f in faturas), 0)
        context['a_pagar'] = sum((f.a_pagar for f in faturas), 0)
        return context


class FaturaCreateView(RedirectFiltrosMixin, CreateView):
    model = Fatura
    form_class = FaturaForm
    template_name = 'cartoes/fatura_form.html'
    lista_url = 'cartoes:lista'

    def get_initial(self):
        initial = super().get_initial()
        initial['ano'] = ano_request(self.request)
        mes = mes_request(self.request)
        if mes:
            initial['mes'] = mes
        if self.request.GET.get('cartao'):
            initial['cartao'] = self.request.GET['cartao']
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Fatura cadastrada.')
        return super().form_valid(form)


class FaturaUpdateView(RedirectFiltrosMixin, UpdateView):
    model = Fatura
    form_class = FaturaForm
    template_name = 'cartoes/fatura_form.html'
    lista_url = 'cartoes:lista'

    def form_valid(self, form):
        messages.success(self.request, 'Fatura atualizada.')
        return super().form_valid(form)


class FaturaDetailView(DetailView):
    model = Fatura
    template_name = 'cartoes/detalhe.html'
    context_object_name = 'fatura'

    def get_queryset(self):
        return Fatura.objects.select_related('cartao').prefetch_related('itens')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_item'] = ItemFaturaForm()
        context['form_importar'] = ImportarItensCSVForm()
        context['total'] = self.object.total
        context['voltar'] = url_filtrada(self.request, 'cartoes:lista')
        return context


def adicionar_item(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    if request.method == 'POST':
        form = ItemFaturaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.fatura = fatura
            propagados = salvar_item_com_parcelas(item)
            if propagados:
                messages.success(
                    request,
                    f'Item adicionado. {propagados} parcela(s) lançada(s) nas faturas seguintes.',
                )
            else:
                messages.success(request, 'Item adicionado à fatura.')
        else:
            messages.error(request, 'Não foi possível adicionar o item. Confira os dados.')
    return _redirect_detalhe(request, pk)


@require_POST
def importar_itens(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    form = ImportarItensCSVForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Não foi possível importar. Envie um CSV ou XLSX válido.')
        return _redirect_detalhe(request, pk)

    try:
        criados, propagados, erros = importar_itens_arquivo(
            fatura, form.cleaned_data['arquivo'],
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return _redirect_detalhe(request, pk)
    if criados:
        msg = f'{criados} item(ns) importado(s).'
        if propagados:
            msg += f' {propagados} parcela(s) lançada(s) nas faturas seguintes.'
        messages.success(request, msg)
    elif not erros:
        messages.warning(request, 'Nenhum item encontrado no arquivo.')
    if erros:
        amostra = '; '.join(erros[:5])
        extra = f' (+{len(erros) - 5} erro(s))' if len(erros) > 5 else ''
        messages.error(request, f'Algumas linhas falharam: {amostra}{extra}')
    return _redirect_detalhe(request, pk)


def _redirect_detalhe(request, pk):
    url = reverse('cartoes:detalhe', args=[pk])
    query = request.GET.urlencode()
    return redirect(f'{url}?{query}' if query else url)


def excluir_item(request, pk):
    item = get_object_or_404(ItemFatura, pk=pk)
    fatura_id = item.fatura_id
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item excluído.')
        return _redirect_detalhe(request, fatura_id)
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': item,
        'titulo': 'Excluir item da fatura',
        'voltar': reverse('cartoes:detalhe', args=[fatura_id]),
    })


def excluir_fatura(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk)
    if request.method == 'POST':
        fatura.delete()
        messages.success(request, 'Fatura excluída.')
        return redirect_filtrado(request, 'cartoes:lista')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': fatura,
        'titulo': 'Excluir fatura',
        'voltar': url_filtrada(request, 'cartoes:lista'),
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


def cadastros_cartoes(request):
    return render(request, 'cartoes/cadastros.html', {
        'cartoes': Cartao.objects.all(),
        'voltar': url_filtrada(request, 'cartoes:lista'),
    })


def novo_cartao(request):
    if request.method == 'POST':
        form = CartaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cartão cadastrado.')
            return redirect_filtrado(request, 'cartoes:cadastros')
    else:
        form = CartaoForm()
    return render(request, 'cartoes/cartao_form.html', {
        'form': form,
        'voltar': url_filtrada(request, 'cartoes:cadastros'),
    })


def editar_cartao(request, pk):
    cartao = get_object_or_404(Cartao, pk=pk)
    if request.method == 'POST':
        form = CartaoForm(request.POST, instance=cartao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cartão atualizado.')
            return redirect_filtrado(request, 'cartoes:cadastros')
    else:
        form = CartaoForm(instance=cartao)
    return render(request, 'cartoes/cartao_form.html', {
        'form': form,
        'voltar': url_filtrada(request, 'cartoes:cadastros'),
    })


def excluir_cartao(request, pk):
    cartao = get_object_or_404(Cartao, pk=pk)
    qtd = cartao.faturas.count()
    if request.method == 'POST':
        cartao.delete()
        messages.success(request, 'Cartão excluído.')
        return redirect_filtrado(request, 'cartoes:cadastros')
    return render(request, 'inicio/confirmar_exclusao.html', {
        'objeto': cartao,
        'titulo': 'Excluir cartão',
        'aviso': f'Isso também apaga {qtd} fatura(s) deste cartão.' if qtd else '',
        'voltar': url_filtrada(request, 'cartoes:cadastros'),
    })


def _copiar_itens_fatura(origem, nova, request):
    if request.POST.get('copiar_itens'):
        for item in origem.itens.all():
            ItemFatura.objects.create(
                fatura=nova,
                descricao=item.descricao,
                valor=item.valor,
                quantidade_parcelas=item.quantidade_parcelas,
                parcela_atual=item.parcela_atual,
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
            salvar_item_com_parcelas(novo)
            return JsonResponse({'ok': True})
        html = render_to_string(
            'includes/form_campos.html',
            {'form': form},
            request=request,
        )
        return JsonResponse({'ok': False, 'html': html}, status=400)
    form = ItemFaturaForm(
        prefix=PREFIXO,
        initial={
            'descricao': item.descricao,
            'valor': item.valor,
            'quantidade_parcelas': item.quantidade_parcelas,
            'parcela_atual': item.parcela_atual,
        },
    )
    html = render_to_string(
        'includes/form_campos.html',
        {'form': form},
        request=request,
    )
    return JsonResponse({'ok': True, 'html': html, 'titulo': 'Duplicar item'})
