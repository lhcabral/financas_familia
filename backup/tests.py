import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backup import servicos
from backup.forms import AgendamentoBackupForm
from backup.models import AgendamentoBackup
from planejamento.models import PerfilFinanceiro


def _momento(*args):
    return timezone.make_aware(datetime(*args))


def _exportar_falso(arquivo):
    arquivo.write(b'-- backup de teste\n')


class PastaTemporariaMixin:
    def setUp(self):
        super().setUp()
        self.pasta = Path(tempfile.mkdtemp())
        configuracao = override_settings(BACKUP_DIR=self.pasta)
        configuracao.enable()
        self.addCleanup(configuracao.disable)
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)


class AgendamentoTests(TestCase):
    def _agendamento(self, **campos):
        agendamento = AgendamentoBackup.objects.create(
            dias_semana=campos.pop('dias_semana', '0,2'),
            horarios=campos.pop('horarios', '02:00,14:30'),
            **campos,
        )
        AgendamentoBackup.objects.filter(pk=agendamento.pk).update(atualizado_em=_momento(2026, 10, 12, 1, 0))
        agendamento.refresh_from_db()
        return agendamento

    def test_proxima_execucao_respeita_dias_e_horarios(self):
        agendamento = self._agendamento()
        # 12/10/2026 é segunda; quarta é 14/10.
        self.assertEqual(agendamento.proxima_execucao(_momento(2026, 10, 12, 1, 0)), _momento(2026, 10, 12, 2, 0))
        self.assertEqual(agendamento.proxima_execucao(_momento(2026, 10, 12, 2, 0)), _momento(2026, 10, 12, 14, 30))
        self.assertEqual(agendamento.proxima_execucao(_momento(2026, 10, 12, 15, 0)), _momento(2026, 10, 14, 2, 0))
        self.assertEqual(agendamento.proxima_execucao(_momento(2026, 10, 14, 15, 0)), _momento(2026, 10, 19, 2, 0))

    def test_pendente_quando_horario_ja_passou(self):
        agendamento = self._agendamento()
        self.assertFalse(agendamento.pendente(_momento(2026, 10, 12, 1, 59)))
        self.assertTrue(agendamento.pendente(_momento(2026, 10, 12, 2, 0)))
        agendamento.ultima_execucao = _momento(2026, 10, 12, 2, 0)
        self.assertFalse(agendamento.pendente(_momento(2026, 10, 12, 14, 0)))

    def test_so_um_processo_consegue_reservar_a_execucao(self):
        agendamento = self._agendamento()
        concorrente = AgendamentoBackup.objects.get(pk=agendamento.pk)
        agora = _momento(2026, 10, 12, 2, 0)
        self.assertTrue(agendamento.reservar_execucao(agora))
        self.assertFalse(concorrente.reservar_execucao(agora))

    def test_formulario_normaliza_horarios_e_dias(self):
        form = AgendamentoBackupForm(data={
            'dias': ['4', '0'], 'horarios': '14h30; 2:00, 02:00', 'retencao_dias': 7, 'ativo': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        agendamento = form.save()
        self.assertEqual(agendamento.dias_semana, '0,4')
        self.assertEqual(agendamento.horarios, '02:00,14:30')
        self.assertEqual(agendamento.dias_rotulo, 'seg, sex')

    def test_formulario_recusa_horario_invalido(self):
        form = AgendamentoBackupForm(data={'dias': ['0'], 'horarios': '25:00', 'retencao_dias': 7})
        self.assertFalse(form.is_valid())
        self.assertIn('horarios', form.errors)


@mock.patch('backup.servicos.exportar', side_effect=_exportar_falso)
class ExecucaoAgendadaTests(PastaTemporariaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.agendamento = AgendamentoBackup.objects.create(dias_semana='0,1,2,3,4,5,6', horarios='02:00', retencao_dias=7)
        AgendamentoBackup.objects.filter(pk=self.agendamento.pk).update(
            atualizado_em=timezone.now() - timedelta(days=2),
        )

    def test_executa_pendente_e_registra(self, exportar):
        arquivos = servicos.executar_pendentes()
        self.assertEqual(len(arquivos), 1)
        self.assertTrue(arquivos[0].name.startswith(self.agendamento.prefixo_arquivo))
        self.agendamento.refresh_from_db()
        self.assertIsNotNone(self.agendamento.ultima_execucao)
        self.assertEqual(servicos.executar_pendentes(), [])

    def test_substitui_backups_mais_antigos_que_o_periodo(self, exportar):
        antigo = self.pasta / servicos.nome_arquivo('agendado-%s' % self.agendamento.pk, timezone.now() - timedelta(days=8))
        recente = self.pasta / servicos.nome_arquivo('agendado-%s' % self.agendamento.pk, timezone.now() - timedelta(days=3))
        de_outro = self.pasta / servicos.nome_arquivo('agendado-999', timezone.now() - timedelta(days=30))
        for arquivo in (antigo, recente, de_outro):
            arquivo.write_text('x')
        servicos.executar_pendentes()
        self.assertFalse(antigo.exists())
        self.assertTrue(recente.exists())
        self.assertTrue(de_outro.exists())

    def test_falha_fica_registrada_no_agendamento(self, exportar):
        exportar.side_effect = servicos.ErroBackup('pg_dump falhou: sem acesso')
        self.assertEqual(servicos.executar_pendentes(), [])
        self.agendamento.refresh_from_db()
        self.assertIn('sem acesso', self.agendamento.ultimo_erro)
        self.assertEqual(list(self.pasta.iterdir()), [])


class ValidacaoArquivoTests(PastaTemporariaMixin, TestCase):
    def test_recusa_backup_de_outro_tipo_de_banco(self):
        outro = 'sqlite' if connection.vendor == 'postgresql' else 'postgresql'
        caminho = self.pasta / 'outro.sql'
        caminho.write_text(f'-- Finanças da família | backup completo | banco: {outro} | gerado em hoje\n')
        with self.assertRaisesMessage(servicos.ErroBackup, outro):
            servicos.importar(caminho)

    def test_recusa_arquivo_binario(self):
        caminho = self.pasta / 'binario.sql'
        caminho.write_bytes(b'\xff\xfe\x00\x00')
        with self.assertRaisesMessage(servicos.ErroBackup, 'UTF-8'):
            servicos.importar(caminho)


class ViewsTests(PastaTemporariaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user('admin', password='senha-forte-123', is_staff=True)
        self.client.force_login(self.admin)

    def test_somente_administrador_acessa(self):
        comum = User.objects.create_user('comum', password='senha-forte-123')
        self.client.force_login(comum)
        self.assertEqual(self.client.get(reverse('backup:painel')).status_code, 403)

    def test_painel_lista_agendamentos_e_arquivos(self):
        AgendamentoBackup.objects.create(dias_semana='0', horarios='03:00')
        (self.pasta / servicos.nome_arquivo(servicos.PREFIXO_ANTES_IMPORTAR)).write_text('x')
        resposta = self.client.get(reverse('backup:painel'))
        self.assertContains(resposta, 'seg')
        self.assertContains(resposta, 'Cópia antes de importar')

    @mock.patch('backup.servicos.exportar', side_effect=_exportar_falso)
    def test_exportar_baixa_arquivo_sem_guardar_no_servidor(self, exportar):
        resposta = self.client.post(reverse('backup:exportar'))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('attachment', resposta['Content-Disposition'])
        self.assertIn('.sql', resposta['Content-Disposition'])
        self.assertEqual(b''.join(resposta.streaming_content), b'-- backup de teste\n')
        self.assertEqual(list(self.pasta.iterdir()), [])

    def test_baixar_e_excluir_arquivo_do_servidor(self):
        arquivo = self.pasta / 'agendado-1_2026-10-14_020000.sql'
        arquivo.write_text('conteudo')
        resposta = self.client.get(reverse('backup:arquivo_baixar', args=[arquivo.name]))
        self.assertEqual(b''.join(resposta.streaming_content), b'conteudo')
        self.client.post(reverse('backup:arquivo_excluir', args=[arquivo.name]))
        self.assertFalse(arquivo.exists())

    def test_nao_baixa_fora_da_pasta_de_backups(self):
        self.assertEqual(self.client.get(reverse('backup:arquivo_baixar', args=['..settings.py'])).status_code, 404)
        self.assertEqual(self.client.get('/backup/arquivos/..%2F..%2Fdb.sql/').status_code, 404)

    def test_criar_agendamento(self):
        resposta = self.client.post(reverse('backup:agendamento_novo'), {
            'dias': ['1', '3'], 'horarios': '23:00', 'retencao_dias': 30, 'ativo': 'on',
        })
        self.assertRedirects(resposta, reverse('backup:painel'))
        agendamento = AgendamentoBackup.objects.get()
        self.assertEqual((agendamento.dias_semana, agendamento.retencao_dias), ('1,3', 30))

    @mock.patch('backup.servicos.importar')
    @mock.patch('backup.servicos.exportar', side_effect=_exportar_falso)
    def test_importar_guarda_copia_antes(self, exportar, importar):
        arquivo = SimpleUploadedFile('backup.sql', b'SELECT 1;\n')
        resposta = self.client.post(reverse('backup:importar'), {'arquivo': arquivo, 'confirmar': 'on'})
        self.assertRedirects(resposta, reverse('backup:painel'), fetch_redirect_response=False)
        importar.assert_called_once()
        copias = list(self.pasta.glob(f'{servicos.PREFIXO_ANTES_IMPORTAR}_*.sql'))
        self.assertEqual(len(copias), 1)

    @mock.patch('backup.servicos.importar')
    def test_importar_exige_confirmacao(self, importar):
        arquivo = SimpleUploadedFile('backup.sql', b'SELECT 1;\n')
        resposta = self.client.post(reverse('backup:importar'), {'arquivo': arquivo})
        self.assertEqual(resposta.status_code, 400)
        importar.assert_not_called()


@unittest.skipUnless(connection.vendor == 'sqlite', 'Requer SQLite.')
class RestauracaoSqliteTests(PastaTemporariaMixin, TransactionTestCase):
    def test_exporta_e_restaura_o_banco(self):
        PerfilFinanceiro.objects.create(pk=1, meses_reserva=9)
        caminho = self.pasta / 'completo.sql'
        with open(caminho, 'wb') as arquivo:
            servicos.exportar(arquivo)

        PerfilFinanceiro.objects.filter(pk=1).update(meses_reserva=3)
        AgendamentoBackup.objects.create(dias_semana='0', horarios='01:00')

        servicos.importar(caminho)
        self.assertEqual(PerfilFinanceiro.objects.get(pk=1).meses_reserva, 9)
        self.assertFalse(AgendamentoBackup.objects.exists())

    def test_backup_antigo_ganha_as_tabelas_novas(self):
        caminho = self.pasta / 'antigo.sql'
        with open(caminho, 'wb') as arquivo:
            servicos.exportar(arquivo)
        linhas = caminho.read_text(encoding='utf-8').splitlines(keepends=True)
        caminho.write_text(''.join(
            linha for linha in linhas
            if 'agendamentobackup' not in linha and "'backup'" not in linha
        ), encoding='utf-8')

        servicos.importar(caminho)
        AgendamentoBackup.objects.create(dias_semana='0', horarios='01:00')

    def test_arquivo_com_erro_nao_altera_nada(self):
        PerfilFinanceiro.objects.create(pk=1, meses_reserva=9)
        caminho = self.pasta / 'quebrado.sql'
        caminho.write_text('CREATE TABLE x (id int);\nSELECT * FROM tabela_que_nao_existe;\n')
        with self.assertRaises(servicos.ErroBackup):
            servicos.importar(caminho)
        self.assertEqual(PerfilFinanceiro.objects.get(pk=1).meses_reserva, 9)

    def test_bloqueia_attach_de_outros_arquivos(self):
        alvo = self.pasta / 'invadido.db'
        caminho = self.pasta / 'malicioso.sql'
        caminho.write_text(f"ATTACH DATABASE '{alvo}' AS x;\nCREATE TABLE x.t (id int);\n")
        with self.assertRaises(servicos.ErroBackup):
            servicos.importar(caminho)
        self.assertFalse(alvo.exists())


@unittest.skipUnless(
    connection.vendor == 'postgresql' and shutil.which('pg_dump') and shutil.which('psql'),
    'Requer PostgreSQL com pg_dump e psql.',
)
class RestauracaoPostgresTests(PastaTemporariaMixin, TransactionTestCase):
    def test_exporta_e_restaura_o_banco(self):
        PerfilFinanceiro.objects.create(pk=1, meses_reserva=9)
        caminho = self.pasta / 'completo.sql'
        with open(caminho, 'wb') as arquivo:
            servicos.exportar(arquivo)

        PerfilFinanceiro.objects.filter(pk=1).update(meses_reserva=3)
        AgendamentoBackup.objects.create(dias_semana='0', horarios='01:00')

        servicos.importar(caminho)
        self.assertEqual(PerfilFinanceiro.objects.get(pk=1).meses_reserva, 9)
        self.assertFalse(AgendamentoBackup.objects.exists())

    def test_arquivo_com_erro_nao_altera_nada(self):
        PerfilFinanceiro.objects.create(pk=1, meses_reserva=9)
        caminho = self.pasta / 'quebrado.sql'
        caminho.write_text('DELETE FROM planejamento_perfilfinanceiro;\nSELECT * FROM tabela_que_nao_existe;\n')
        with self.assertRaises(servicos.ErroBackup):
            servicos.importar(caminho)
        self.assertEqual(PerfilFinanceiro.objects.get(pk=1).meses_reserva, 9)

    def test_bloqueia_comandos_de_shell_do_psql(self):
        marcador = self.pasta / 'invadido'
        caminho = self.pasta / 'malicioso.sql'
        caminho.write_text(f'\\unrestrict qualquer\n\\! touch {marcador}\nSELECT 1;\n')
        with self.assertRaises(servicos.ErroBackup):
            servicos.importar(caminho)
        self.assertFalse(marcador.exists())
