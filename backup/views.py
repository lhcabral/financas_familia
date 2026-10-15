import os
import tempfile
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from backup import servicos
from backup.forms import AgendamentoBackupForm, ImportarBackupForm
from backup.models import AgendamentoBackup


def somente_administrador(view):
    @wraps(view)
    def interna(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return interna


def _painel(request, form_agendamento=None, form_importar=None, status=200):
    agendamentos = list(AgendamentoBackup.objects.all())
    for agendamento in agendamentos:
        agendamento.proxima = agendamento.proxima_execucao() if agendamento.ativo else None
    return render(request, 'backup/painel.html', {
        'agendamentos': agendamentos,
        'arquivos': servicos.listar_arquivos(agendamentos),
        'form_agendamento': form_agendamento or AgendamentoBackupForm(),
        'form_importar': form_importar or ImportarBackupForm(),
    }, status=status)


@somente_administrador
def painel(request):
    return _painel(request)


@somente_administrador
@require_POST
def exportar(request):
    arquivo = tempfile.TemporaryFile()
    try:
        servicos.exportar(arquivo)
    except servicos.ErroBackup as erro:
        arquivo.close()
        messages.error(request, f'Não foi possível exportar: {erro}')
        return redirect('backup:painel')
    arquivo.seek(0)
    return FileResponse(arquivo, as_attachment=True, filename=servicos.nome_arquivo('financas-familia'))


@somente_administrador
@require_POST
def importar(request):
    form = ImportarBackupForm(request.POST, request.FILES)
    if not form.is_valid():
        return _painel(request, form_importar=form, status=400)

    with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as temporario:
        for pedaco in form.cleaned_data['arquivo'].chunks():
            temporario.write(pedaco)
    try:
        copia = servicos.salvar_no_servidor(servicos.PREFIXO_ANTES_IMPORTAR)
        servicos.importar(temporario.name)
    except servicos.ErroBackup as erro:
        messages.error(request, f'Falha na importação: {erro}')
    else:
        messages.success(
            request,
            f'Backup importado. Os dados anteriores ficaram salvos em "{copia.name}". '
            'Se a sessão expirar, entre novamente.',
        )
    finally:
        os.unlink(temporario.name)
    return redirect('backup:painel')


@somente_administrador
@require_POST
def agendamento_novo(request):
    form = AgendamentoBackupForm(request.POST)
    if not form.is_valid():
        return _painel(request, form_agendamento=form, status=400)
    form.save()
    messages.success(request, 'Agendamento criado.')
    return redirect('backup:painel')


@somente_administrador
def agendamento_editar(request, pk):
    agendamento = get_object_or_404(AgendamentoBackup, pk=pk)
    form = AgendamentoBackupForm(request.POST or None, instance=agendamento)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Agendamento atualizado.')
        return redirect('backup:painel')
    return render(request, 'backup/agendamento_form.html', {'form': form, 'agendamento': agendamento})


@somente_administrador
@require_POST
def agendamento_excluir(request, pk):
    get_object_or_404(AgendamentoBackup, pk=pk).delete()
    messages.success(request, 'Agendamento excluído. Os arquivos já gerados continuam na lista.')
    return redirect('backup:painel')


@somente_administrador
@require_POST
def agendamento_executar(request, pk):
    agendamento = get_object_or_404(AgendamentoBackup, pk=pk)
    try:
        arquivo = servicos.executar_agendamento(agendamento)
    except servicos.ErroBackup as erro:
        messages.error(request, f'Falha ao gerar o backup: {erro}')
    else:
        messages.success(request, f'Backup "{arquivo.name}" gerado no servidor.')
    return redirect('backup:painel')


@somente_administrador
def arquivo_baixar(request, nome):
    caminho = servicos.arquivo_do_servidor(nome)
    if caminho is None:
        raise Http404('Backup não encontrado.')
    return FileResponse(open(caminho, 'rb'), as_attachment=True, filename=caminho.name)


@somente_administrador
@require_POST
def arquivo_excluir(request, nome):
    caminho = servicos.arquivo_do_servidor(nome)
    if caminho is None:
        raise Http404('Backup não encontrado.')
    caminho.unlink()
    messages.success(request, f'Backup "{nome}" excluído do servidor.')
    return redirect('backup:painel')
