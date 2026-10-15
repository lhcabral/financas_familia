import logging
import threading
import time

from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError

from backup import servicos

INTERVALO_SEGUNDOS = 60

logger = logging.getLogger(__name__)
_trava = threading.Lock()
_iniciado = False


def _laco():
    while True:
        try:
            servicos.executar_pendentes()
        except (OperationalError, ProgrammingError):
            logger.warning('Banco indisponível para verificar backups agendados.')
        except Exception:
            logger.exception('Falha ao verificar backups agendados.')
        finally:
            connection.close()
        time.sleep(INTERVALO_SEGUNDOS)


def iniciar():
    """Sobe uma thread por processo do servidor que roda os backups no horário."""
    global _iniciado
    if not settings.BACKUP_AGENDADOR_ATIVO:
        return
    with _trava:
        if _iniciado:
            return
        _iniciado = True
    threading.Thread(target=_laco, name='agendador-backup', daemon=True).start()
