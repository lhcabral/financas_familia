from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

PREFIXO = 'duplicar'


def _inicial(instance, form_class):
    dados = {}
    for nome in form_class._meta.fields:
        campo = instance._meta.get_field(nome)
        if campo.is_relation and not campo.many_to_many:
            dados[nome] = getattr(instance, f'{nome}_id')
        else:
            dados[nome] = getattr(instance, nome)
    return dados


def duplicar_objeto(
    request,
    model,
    form_class,
    pk,
    titulo,
    extra_template=None,
    apos_salvar=None,
):
    origem = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        form = form_class(request.POST, prefix=PREFIXO)
        if form.is_valid():
            novo = form.save()
            if apos_salvar:
                apos_salvar(origem, novo, request)
            return JsonResponse({'ok': True})
        html = render_to_string(
            'includes/form_campos.html',
            {'form': form, 'extra_template': extra_template},
            request=request,
        )
        return JsonResponse({'ok': False, 'html': html}, status=400)

    form = form_class(prefix=PREFIXO, initial=_inicial(origem, form_class))
    html = render_to_string(
        'includes/form_campos.html',
        {'form': form, 'extra_template': extra_template},
        request=request,
    )
    return JsonResponse({'ok': True, 'html': html, 'titulo': titulo})
