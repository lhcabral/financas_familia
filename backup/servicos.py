import logging
import os
import re
import secrets
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from backup.models import AgendamentoBackup

TEMPO_LIMITE = 900
FORMATO_DATA = '%Y-%m-%d_%H%M%S'
NOME_VALIDO = re.compile(r'^[\w.-]+\.sql$')
NOME_COM_DATA = re.compile(r'^(?P<prefixo>[\w-]+)_(?P<data>\d{4}-\d{2}-\d{2}_\d{6})\.sql$')
CABECALHO = re.compile(r'^-- Finanças da família .* banco: (\w+)', re.MULTILINE)
LINHA_RESTRICT = re.compile(r'^\\(un)?restrict\s+\S+\s*$')
PREFIXO_ANTES_IMPORTAR = 'antes-importacao'

logger = logging.getLogger(__name__)


class ErroBackup(Exception):
    pass


def pasta_backups():
    pasta = Path(settings.BACKUP_DIR)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def nome_arquivo(prefixo='backup', momento=None):
    momento = timezone.localtime(momento or timezone.now())
    return f'{prefixo}_{momento:{FORMATO_DATA}}.sql'


def _cabecalho():
    agora = timezone.localtime()
    return f'-- Finanças da família | backup completo | banco: {connection.vendor} | gerado em {agora:%d/%m/%Y %H:%M}\n'


def _ambiente_postgres():
    config = connection.settings_dict
    ambiente = os.environ.copy()
    for variavel, chave in (
        ('PGHOST', 'HOST'),
        ('PGPORT', 'PORT'),
        ('PGUSER', 'USER'),
        ('PGPASSWORD', 'PASSWORD'),
        ('PGDATABASE', 'NAME'),
    ):
        if config.get(chave):
            ambiente[variavel] = str(config[chave])
    return ambiente


def _rodar(comando, **kwargs):
    try:
        resultado = subprocess.run(
            comando,
            env=_ambiente_postgres(),
            stderr=subprocess.PIPE,
            timeout=TEMPO_LIMITE,
            check=False,
            **kwargs,
        )
    except FileNotFoundError as erro:
        raise ErroBackup(f'Programa "{comando[0]}" não encontrado no servidor. Instale o cliente do PostgreSQL.') from erro
    except subprocess.TimeoutExpired as erro:
        raise ErroBackup(f'"{comando[0]}" demorou mais de {TEMPO_LIMITE // 60} minutos.') from erro
    if resultado.returncode != 0:
        detalhe = resultado.stderr.decode('utf-8', 'replace').strip().splitlines()
        raise ErroBackup(f'{comando[0]} falhou: ' + ' '.join(detalhe[-3:]))


def exportar(arquivo):
    """Grava no arquivo binário aberto um .sql com estrutura e dados de todo o banco."""
    if connection.vendor == 'postgresql':
        arquivo.write(_cabecalho().encode())
        arquivo.flush()
        _rodar(
            ['pg_dump', '--clean', '--if-exists', '--no-owner', '--no-privileges', '--encoding=UTF8'],
            stdout=arquivo,
        )
    elif connection.vendor == 'sqlite':
        connection.ensure_connection()
        arquivo.write(_cabecalho().encode())
        for linha in connection.connection.iterdump():
            arquivo.write(linha.encode() + b'\n')
    else:
        raise ErroBackup(f'Banco "{connection.vendor}" não suportado para backup.')


def _validar_origem(caminho):
    with open(caminho, 'rb') as arquivo:
        inicio = arquivo.read(4096)
    try:
        texto = inicio.decode('utf-8')
    except UnicodeDecodeError as erro:
        raise ErroBackup('O arquivo não é um .sql em texto (UTF-8).') from erro
    encontrado = CABECALHO.search(texto)
    if encontrado:
        banco = encontrado.group(1)
    elif 'PostgreSQL database dump' in texto:
        banco = 'postgresql'
    else:
        banco = None
    if banco and banco != connection.vendor:
        raise ErroBackup(f'Este backup é de um banco {banco}, mas o sistema usa {connection.vendor}.')


def _importar_postgres(caminho):
    chave = secrets.token_hex(16)
    tabelas = connection.introspection.table_names()
    connection.close()
    with tempfile.NamedTemporaryFile('w', suffix='.sql', encoding='utf-8', delete=False) as roteiro:
        # \restrict bloqueia meta-comandos do psql (ex.: \!) vindos do arquivo enviado.
        roteiro.write(f'\\restrict {chave}\n')
        roteiro.write('SET client_min_messages = warning;\n')
        for tabela in tabelas:
            roteiro.write(f'DROP TABLE IF EXISTS "{tabela}" CASCADE;\n')
        with open(caminho, encoding='utf-8') as origem:
            for linha in origem:
                if not LINHA_RESTRICT.match(linha):
                    roteiro.write(linha)
        roteiro.write(f'\n\\unrestrict {chave}\n')
    try:
        _rodar(
            ['psql', '-X', '--quiet', '--single-transaction', '-v', 'ON_ERROR_STOP=1', '-f', roteiro.name],
            stdout=subprocess.DEVNULL,
        )
    finally:
        os.unlink(roteiro.name)


def _negar_attach(acao, *args):
    return sqlite3.SQLITE_DENY if acao in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH) else sqlite3.SQLITE_OK


def _importar_sqlite(caminho):
    temporario = sqlite3.connect(':memory:')
    try:
        temporario.set_authorizer(_negar_attach)
        with open(caminho, encoding='utf-8') as arquivo:
            temporario.executescript(arquivo.read())
        connection.ensure_connection()
        temporario.backup(connection.connection)
    except sqlite3.Error as erro:
        raise ErroBackup(f'O arquivo tem erro de SQL: {erro}') from erro
    finally:
        temporario.close()
    connection.close()


def importar(caminho):
    """Substitui todo o banco pelo conteúdo do .sql. Em caso de erro nada é alterado."""
    try:
        _validar_origem(caminho)
        if connection.vendor == 'postgresql':
            _importar_postgres(caminho)
        elif connection.vendor == 'sqlite':
            _importar_sqlite(caminho)
        else:
            raise ErroBackup(f'Banco "{connection.vendor}" não suportado para backup.')
    except ErroBackup as erro:
        raise ErroBackup(f'{erro} Nenhum dado foi alterado.') from erro
    # Backups antigos podem não ter as tabelas criadas depois deles.
    try:
        call_command('migrate', interactive=False, verbosity=0)
    except Exception as erro:
        raise ErroBackup(f'Dados importados, mas falhou ao atualizar a estrutura (rode "manage.py migrate"): {erro}') from erro


def salvar_no_servidor(prefixo):
    """Gera o backup na pasta do servidor; o arquivo só aparece completo."""
    final = pasta_backups() / nome_arquivo(prefixo)
    parcial = final.with_suffix('.parcial')
    try:
        with open(parcial, 'wb') as arquivo:
            exportar(arquivo)
        parcial.rename(final)
    finally:
        parcial.unlink(missing_ok=True)
    return final


def arquivo_do_servidor(nome):
    if not NOME_VALIDO.match(nome):
        return None
    caminho = pasta_backups() / nome
    return caminho if caminho.is_file() else None


def data_do_arquivo(caminho):
    encontrado = NOME_COM_DATA.match(caminho.name)
    if encontrado:
        try:
            return timezone.make_aware(datetime.strptime(encontrado.group('data'), FORMATO_DATA))
        except ValueError:
            pass
    return datetime.fromtimestamp(caminho.stat().st_mtime, tz=timezone.utc)


def _origem(caminho, agendamentos):
    encontrado = NOME_COM_DATA.match(caminho.name)
    prefixo = encontrado.group('prefixo') if encontrado else ''
    if prefixo == PREFIXO_ANTES_IMPORTAR:
        return 'Cópia antes de importar'
    if prefixo.startswith('agendado-'):
        agendamento = agendamentos.get(prefixo.removeprefix('agendado-'))
        return f'Agendado: {agendamento}' if agendamento else 'Agendamento removido'
    return 'Outro'


def listar_arquivos(agendamentos=()):
    por_id = {str(agendamento.pk): agendamento for agendamento in agendamentos}
    arquivos = [
        {
            'nome': caminho.name,
            'tamanho': caminho.stat().st_size,
            'criado_em': data_do_arquivo(caminho),
            'origem': _origem(caminho, por_id),
        }
        for caminho in pasta_backups().glob('*.sql')
        if caminho.is_file()
    ]
    return sorted(arquivos, key=lambda item: item['criado_em'], reverse=True)


def aplicar_retencao(agendamento, manter):
    """Apaga os backups do agendamento mais antigos que o período escolhido."""
    limite = timezone.now() - timedelta(days=agendamento.retencao_dias)
    removidos = 0
    for caminho in pasta_backups().glob(f'{agendamento.prefixo_arquivo}*.sql'):
        if caminho != manter and data_do_arquivo(caminho) < limite:
            caminho.unlink(missing_ok=True)
            removidos += 1
    return removidos


def executar_agendamento(agendamento):
    registros = AgendamentoBackup.objects.filter(pk=agendamento.pk)
    try:
        arquivo = salvar_no_servidor(agendamento.prefixo_arquivo.rstrip('_'))
    except Exception as erro:
        registros.update(ultimo_erro=str(erro) or erro.__class__.__name__)
        raise
    registros.update(ultimo_erro='')
    aplicar_retencao(agendamento, manter=arquivo)
    return arquivo


def executar_pendentes(agora=None):
    """Roda os agendamentos cujo horário já chegou. Seguro com vários processos."""
    agora = agora or timezone.now()
    executados = []
    for agendamento in AgendamentoBackup.objects.filter(ativo=True):
        if not agendamento.pendente(agora) or not agendamento.reservar_execucao(agora):
            continue
        try:
            executados.append(executar_agendamento(agendamento))
        except Exception:
            logger.exception('Falha no backup agendado %s', agendamento.pk)
    return executados
