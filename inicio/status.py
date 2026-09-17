from django.core.exceptions import ValidationError
from django.http import JsonResponse

from cartoes.models import Cartao, Fatura, ItemFatura
from inicio.constants import STATUS_ABERTO, STATUS_CARTAO, STATUS_CHOICES, STATUS_PAGAMENTO

STATUS_VALIDOS = {codigo for codigo, _ in STATUS_CHOICES}
STATUS_FATURA = {codigo for codigo, _ in STATUS_PAGAMENTO}


def aplicar_status(obj, status, cartao_id=None, descricao_item='', valor=None, ano=None, mes=None):
    """Atualiza o status. Cartão fecha a conta e lança o valor na fatura do mês."""
    if status not in STATUS_VALIDOS:
        raise ValidationError('Status inválido.')

    if status == STATUS_CARTAO:
        _lancar_no_cartao(obj, cartao_id, descricao_item, valor, ano, mes)
    else:
        _remover_item_cartao(obj)

    obj.status = status
    campos = ['status']
    if hasattr(obj, 'item_fatura_id'):
        campos.append('item_fatura')
    obj.save(update_fields=campos)
    return obj


def json_status(obj, extra=None):
    dados = {
        'ok': True,
        'status': obj.status,
        'status_display': obj.get_status_display(),
    }
    if extra:
        dados.update(extra)
    return JsonResponse(dados)


def json_erro(erro, status_http=400):
    if isinstance(erro, ValidationError):
        mensagem = erro.messages[0] if getattr(erro, 'messages', None) else str(erro)
    else:
        mensagem = str(erro)
    return JsonResponse({'ok': False, 'erro': mensagem}, status=status_http)


def aplicar_status_fatura(fatura, status):
    if status not in STATUS_FATURA:
        raise ValidationError('A fatura só pode ficar Aberta ou Fechada.')
    fatura.status = status
    fatura.save(update_fields=['status'])
    return fatura


def _lancar_no_cartao(obj, cartao_id, descricao_item, valor, ano, mes):
    if not cartao_id:
        raise ValidationError('Selecione um cartão para fechar esta conta.')
    try:
        cartao = Cartao.objects.get(pk=cartao_id)
    except (Cartao.DoesNotExist, ValueError, TypeError) as exc:
        raise ValidationError('Cartão não encontrado.') from exc

    fatura, _ = Fatura.objects.get_or_create(
        cartao=cartao,
        ano=ano,
        mes=mes,
        defaults={'status': STATUS_ABERTO},
    )
    item = getattr(obj, 'item_fatura', None)
    if item:
        item.fatura = fatura
        item.descricao = descricao_item
        item.valor = valor
        item.save(update_fields=['fatura', 'descricao', 'valor'])
    else:
        obj.item_fatura = ItemFatura.objects.create(
            fatura=fatura,
            descricao=descricao_item,
            valor=valor,
        )


def _remover_item_cartao(obj):
    item = getattr(obj, 'item_fatura', None)
    if not item:
        return
    obj.item_fatura = None
    item.delete()
