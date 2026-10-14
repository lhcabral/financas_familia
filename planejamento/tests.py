import io
import json
from datetime import date
from decimal import Decimal
from unittest import mock
from urllib.error import URLError

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase

from cartoes.models import Cartao, Fatura, ItemFatura
from despesas_basicas.models import DespesaBasica
from imoveis_transporte.models import Consorcio, ParcelaConsorcio
from inicio.constants import STATUS_ABERTO
from inicio.models import Receita
from planejamento import banco_central, calculos
from planejamento.models import IndicadorEconomico, PerfilFinanceiro
from planejamento.regras import ATENCAO, CRITICO, gerar_sugestoes

HOJE = date(2026, 10, 15)


def _resposta_api(pontos):
    return io.BytesIO(json.dumps(pontos).encode())


def _salvar_indicadores(**valores):
    for chave, valor in valores.items():
        serie = banco_central.SERIES[chave]
        IndicadorEconomico.objects.create(
            chave=chave,
            codigo_sgs=serie['codigo'],
            nome=serie['nome'],
            valor=Decimal(valor),
            data_referencia=HOJE,
        )


class BancoCentralTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch('planejamento.banco_central.urlopen')
    def test_buscar_serie_pega_o_ponto_mais_recente(self, urlopen):
        urlopen.return_value = _resposta_api([
            {'data': '09/10/2026', 'valor': '13.65'},
            {'data': '08/10/2026', 'valor': '13.40'},
        ])
        self.assertEqual(banco_central.buscar_serie(4389), (date(2026, 10, 9), Decimal('13.65')))

    @mock.patch('planejamento.banco_central.urlopen')
    def test_resposta_estranha_vira_erro_do_banco_central(self, urlopen):
        urlopen.return_value = _resposta_api([{'data': 'ontem'}])
        with self.assertRaises(banco_central.ErroBancoCentral):
            banco_central.buscar_serie(432)

    @mock.patch('planejamento.banco_central.buscar_serie')
    def test_atualizar_salva_todas_as_series(self, buscar):
        buscar.return_value = (HOJE, Decimal('10.5'))
        erros = banco_central.atualizar_indicadores(forcar=True)
        self.assertEqual(erros, [])
        self.assertEqual(IndicadorEconomico.objects.count(), len(banco_central.SERIES))
        self.assertEqual(banco_central.valor(banco_central.indicadores(), 'cdi'), Decimal('10.5'))

    @mock.patch('planejamento.banco_central.buscar_serie')
    def test_sem_internet_mantem_valores_salvos(self, buscar):
        _salvar_indicadores(cdi='12.00')
        buscar.side_effect = URLError('sem rede')
        erros = banco_central.atualizar_indicadores(forcar=True)
        self.assertEqual(len(erros), 1)
        self.assertEqual(buscar.call_count, 1)
        self.assertEqual(banco_central.valor(banco_central.indicadores(), 'cdi'), Decimal('12.00'))

    @mock.patch('planejamento.banco_central.buscar_serie')
    def test_indicadores_recentes_nao_sao_baixados_de_novo(self, buscar):
        _salvar_indicadores(selic='13', cdi='13', ipca_mes='0.5', ipca_12m='4', poupanca='0.6')
        self.assertEqual(banco_central.atualizar_indicadores(), [])
        buscar.assert_not_called()


class CalculosTests(TestCase):
    def test_numeros_parcela_entende_rotulo_com_varias_parcelas(self):
        self.assertEqual(calculos.numeros_parcela('14,15,16,17/17', 13), [14, 15, 16, 17])
        self.assertEqual(calculos.numeros_parcela('', 5), [5])
        self.assertEqual(calculos.numeros_parcela('', None), [])

    def test_diagnostico_calcula_percentuais_da_renda(self):
        periodo = {
            'quantidade_meses': 1,
            'receita_total': Decimal('10000'),
            'despesa_total': Decimal('9000'),
            'categorias': {
                'basicas': {'nome': 'Casa', 'total': Decimal('3000')},
                'cartoes': {'nome': 'Cartões', 'total': Decimal('6000')},
            },
        }
        diag = calculos.diagnostico(periodo)
        self.assertAlmostEqual(diag['taxa_poupanca'], 10.0)
        self.assertAlmostEqual(diag['pct_cartao'], 60.0)
        necessidades, variaveis, poupanca = diag['regra_50_30_20']
        self.assertTrue(necessidades['dentro'])
        self.assertFalse(variaveis['dentro'])
        self.assertFalse(poupanca['dentro'])

    def test_simulacao_cdi_rende_mais_que_parado(self):
        linha = calculos.simular_investimento(Decimal('1000'), Decimal('12'), Decimal('0.5'), horizontes=(12,))[0]
        self.assertEqual(linha['investido'], Decimal('12000.00'))
        self.assertGreater(linha['cdi'], linha['investido'])
        self.assertGreater(linha['poupanca'], linha['investido'])

    def test_reserva_calcula_meta_e_prazo(self):
        reserva = calculos.reserva_emergencia(Decimal('0'), 6, Decimal('1000'), Decimal('1000'), None)
        self.assertEqual(reserva['meta'], Decimal('6000.00'))
        self.assertEqual(reserva['meses_para_meta'], 6)
        completa = calculos.reserva_emergencia(Decimal('8000'), 6, Decimal('1000'), Decimal('0'), None)
        self.assertEqual(completa['falta'], 0)
        self.assertEqual(completa['excedente'], Decimal('2000.00'))

    def test_desconto_equivalente_cresce_com_os_juros(self):
        self.assertLess(calculos.desconto_equivalente(10, 5), calculos.desconto_equivalente(10, 15))

    def test_compra_parcelada_repetida_nas_faturas_conta_uma_vez(self):
        cartao = Cartao.objects.create(nome='Teste')
        for mes, parcela in ((10, 1), (11, 2)):
            fatura = Fatura.objects.create(cartao=cartao, ano=2026, mes=mes)
            ItemFatura.objects.create(
                fatura=fatura, descricao='LOJA', valor=Decimal('100'),
                quantidade_parcelas=3, parcela_atual=parcela,
            )
        resultado = calculos.compromissos_futuros(HOJE, meses_adiante=3)
        self.assertEqual([item['valor'] for item in resultado['serie']], [Decimal('100'), Decimal('100'), 0])
        self.assertEqual(len(resultado['compromissos']), 1)
        self.assertEqual(resultado['compromissos'][0]['total_restante'], Decimal('200'))

    def test_consorcio_projeta_parcelas_ate_o_fim(self):
        consorcio = Consorcio.objects.create(nome='Cota', total_parcelas=12)
        ParcelaConsorcio.objects.create(
            consorcio=consorcio, ano=2026, mes=10, numero_parcela=10, rotulo_parcela='10/12', valor=Decimal('500'),
        )
        resultado = calculos.compromissos_futuros(HOJE, meses_adiante=3)
        self.assertEqual([item['valor'] for item in resultado['serie']], [Decimal('500'), Decimal('500'), 0])

    def test_consorcio_quitado_por_lance_nao_gera_parcelas(self):
        consorcio = Consorcio.objects.create(nome='Carro', total_parcelas=17)
        ParcelaConsorcio.objects.create(
            consorcio=consorcio, ano=2026, mes=9, numero_parcela=13,
            rotulo_parcela='14,15,16,17/17', valor=Decimal('4000'),
        )
        self.assertEqual(calculos.compromissos_futuros(HOJE)['compromissos'], [])

    def test_conta_que_subiu_acima_da_inflacao(self):
        for mes, valor in ((1, '100'), (2, '100'), (5, '130'), (6, '130')):
            DespesaBasica.objects.create(ano=2026, mes=mes, descricao='Luz', valor=Decimal(valor))
        for mes in (1, 6):
            DespesaBasica.objects.create(ano=2026, mes=mes, descricao='Água', valor=Decimal('80'))
        resultado = calculos.contas_acima_inflacao(2026, Decimal('4.5'), HOJE)
        self.assertEqual([item['descricao'] for item in resultado], ['Luz'])
        self.assertAlmostEqual(resultado[0]['variacao'], 30.0)

    def test_meses_futuros_ficam_fora_da_comparacao_de_inflacao(self):
        DespesaBasica.objects.create(ano=2026, mes=1, descricao='Luz', valor=Decimal('100'))
        DespesaBasica.objects.create(ano=2026, mes=12, descricao='Luz', valor=Decimal('200'))
        self.assertEqual(calculos.contas_acima_inflacao(2026, Decimal('4.5'), HOJE), [])

    def test_alerta_estima_custo_do_atraso(self):
        DespesaBasica.objects.create(
            ano=2026, mes=9, descricao='Escola', valor=Decimal('1000'),
            status=STATUS_ABERTO, dia_vencimento=15,
        )
        alertas = calculos.alertas_vencimento(HOJE)
        self.assertEqual(len(alertas['atrasadas']), 1)
        self.assertEqual(alertas['atrasadas'][0]['dias_atraso'], 30)
        self.assertEqual(alertas['custo_atraso'], Decimal('30.00'))


class RegrasTests(TestCase):
    def _ctx(self, receita, cartao, sobra_media=Decimal('0')):
        periodo = {
            'quantidade_meses': 1,
            'receita_total': Decimal(receita),
            'despesa_total': Decimal(cartao),
            'categorias': {'cartoes': {'nome': 'Cartões', 'total': Decimal(cartao)}},
        }
        diag = calculos.diagnostico(periodo)
        return {
            'periodo_rotulo': 'outubro de 2026',
            'diagnostico': diag,
            'medias': {'receita': Decimal(receita), 'despesa': Decimal(cartao), 'sobra': sobra_media, 'meses': 1},
            'reserva': calculos.reserva_emergencia(Decimal('0'), 6, Decimal(cartao), sobra_media, None),
            'aporte': Decimal('500'),
            'simulacao': [],
            'inflacao': [],
            'compromissos': {
                'proximo_mes': Decimal('0'), 'terminando_em_breve': [], 'liberado_em_breve': Decimal('0'),
            },
            'alertas': {'atrasadas': [], 'proximas': []},
            'cdi': None,
        }

    def test_cartao_acima_do_limite_gera_sugestao_com_economia(self):
        sugestoes = gerar_sugestoes(self._ctx('10000', '4500'))
        cartao = next(s for s in sugestoes if 'cartão' in s.titulo)
        self.assertEqual(cartao.nivel, CRITICO)
        self.assertEqual(cartao.economia_mensal, Decimal('1500.00'))

    def test_gasto_maior_que_renda_vem_primeiro(self):
        sugestoes = gerar_sugestoes(self._ctx('3000', '3500'))
        self.assertEqual(sugestoes[0].titulo, 'Gastos maiores que a renda')
        self.assertEqual(sugestoes[0].economia_mensal, Decimal('500.00'))

    def test_reserva_sem_sobra_pede_atencao(self):
        sugestoes = gerar_sugestoes(self._ctx('10000', '2000'))
        reserva = next(s for s in sugestoes if 'Reserva' in s.titulo)
        self.assertEqual(reserva.nivel, ATENCAO)


@mock.patch('planejamento.banco_central.buscar_serie', return_value=(HOJE, Decimal('12.0')))
class PainelTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user('familia', password='senha-teste-123')
        self.client.login(username='familia', password='senha-teste-123')

    def test_visitante_vai_para_o_login(self, _buscar):
        self.client.logout()
        resposta = self.client.get('/planejamento/')
        self.assertRedirects(resposta, '/entrar/?next=/planejamento/')

    def test_painel_abre_com_dados(self, _buscar):
        Receita.objects.create(ano=2026, mes=1, fonte=Receita.FONTE_SALARIO_LUIZ, valor=Decimal('5000'))
        DespesaBasica.objects.create(ano=2026, mes=1, descricao='Aluguel', valor=Decimal('2000'))
        resposta = self.client.get('/planejamento/?ano=2026')
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Sugestões')
        self.assertContains(resposta, 'Reserva de emergência')

    def test_painel_abre_sem_lancamentos(self, _buscar):
        resposta = self.client.get('/planejamento/?ano=2030&mes=3')
        self.assertEqual(resposta.status_code, 200)

    def test_salvar_reserva_atual(self, _buscar):
        resposta = self.client.post('/planejamento/reserva/?ano=2026', {
            'reserva_atual': '12500.50',
            'meses_reserva': '6',
        })
        self.assertRedirects(resposta, '/planejamento/?ano=2026')
        self.assertEqual(PerfilFinanceiro.obter().reserva_atual, Decimal('12500.50'))

    def test_reserva_negativa_e_recusada(self, _buscar):
        self.client.post('/planejamento/reserva/', {'reserva_atual': '-1', 'meses_reserva': '6'})
        self.assertEqual(PerfilFinanceiro.obter().reserva_atual, 0)
