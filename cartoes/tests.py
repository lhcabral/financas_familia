from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cartoes.models import Cartao, Fatura, ItemFatura
from cartoes.servicos import importar_itens_arquivo, salvar_item_com_parcelas

AMOSTRAS = Path('/home/luiz/Documentos/Desenvolvimento/financas_familia')


class ParcelasItemFaturaTests(TestCase):
    def setUp(self):
        self.cartao = Cartao.objects.create(nome='Nubank Teste')
        self.fatura = Fatura.objects.create(cartao=self.cartao, ano=2026, mes=9)

    def test_propaga_parcelas_restantes(self):
        item = ItemFatura(
            fatura=self.fatura,
            descricao='Notebook',
            valor=Decimal('100.00'),
            quantidade_parcelas=3,
            parcela_atual=1,
        )
        criados = salvar_item_com_parcelas(item)
        self.assertEqual(criados, 2)
        out = Fatura.objects.get(cartao=self.cartao, ano=2026, mes=10)
        nov = Fatura.objects.get(cartao=self.cartao, ano=2026, mes=11)
        self.assertEqual(out.itens.get().parcela_atual, 2)
        self.assertEqual(nov.itens.get().parcela_atual, 3)
        self.assertEqual(nov.itens.get().descricao, 'Notebook')

    def test_nao_propaga_quando_ultima_parcela(self):
        item = ItemFatura(
            fatura=self.fatura,
            descricao='Curso',
            valor=Decimal('50.00'),
            quantidade_parcelas=3,
            parcela_atual=3,
        )
        self.assertEqual(salvar_item_com_parcelas(item), 0)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 1)

    def test_importa_csv_simples(self):
        csv_bytes = (
            'descricao,valor,quantidade_parcelas,parcela_atual\n'
            'Mercado,80.50,1,1\n'
            'TV,200.00,4,2\n'
        ).encode('utf-8')
        criados, propagados, erros = importar_itens_arquivo(self.fatura, BytesIO(csv_bytes))
        self.assertEqual(erros, [])
        self.assertEqual(criados, 2)
        self.assertEqual(propagados, 2)
        self.assertEqual(self.fatura.itens.count(), 2)
        tv = self.fatura.itens.get(descricao='TV')
        self.assertEqual(tv.parcela_atual, 2)
        self.assertEqual(tv.quantidade_parcelas, 4)

    def test_importa_extrato_bradesco_com_parcelas_no_historico(self):
        csv_bytes = (
            'Data;Histórico;Valor(US$);Valor(R$);\n'
            '19/08;DS AUTOS E PECA 1/3;0,00;399,41\n'
            '12/08;CASA DO BANNER 1/2;0,00;1340,00\n'
            '10/08;SALDO ANTERIOR ;0,00;4469,98\n'
            '10/08;PAGTO. POR DEB EM C/C ;0,00;-4469,98\n'
            '08/08;BURGER KING ;0,00;138,70\n'
        ).encode('latin-1')
        criados, propagados, erros = importar_itens_arquivo(self.fatura, BytesIO(csv_bytes))
        self.assertEqual(erros, [])
        self.assertEqual(criados, 3)
        self.assertEqual(propagados, 3)
        autos = self.fatura.itens.get(descricao='DS AUTOS E PECA')
        self.assertEqual(autos.parcela_atual, 1)
        self.assertEqual(autos.quantidade_parcelas, 3)
        self.assertFalse(self.fatura.itens.filter(descricao__icontains='SALDO').exists())

    def test_importa_nubank_csv(self):
        csv_bytes = (
            'date,title,amount\n'
            '2026-07-10,Bmb *Alares,"132,89"\n'
            '2026-07-03,Mp *Onixsemijoias - Parcela 4/4,"155,23"\n'
            '2026-07-03,Pagamento recebido,"- 822,14"\n'
            '2026-07-03,Mp *Onixsemijoias - Parcela 2/4,"82,49"\n'
        ).encode('utf-8')
        arquivo = SimpleUploadedFile('Nubank_2026-08-10.csv', csv_bytes, content_type='text/csv')
        criados, propagados, erros = importar_itens_arquivo(self.fatura, arquivo)
        self.assertEqual(erros, [])
        self.assertEqual(criados, 3)
        # Parcela 2/4 → propaga 3 e 4
        self.assertEqual(propagados, 2)
        onix = self.fatura.itens.get(descricao='Mp *Onixsemijoias', parcela_atual=2)
        self.assertEqual(onix.quantidade_parcelas, 4)
        self.assertFalse(self.fatura.itens.filter(descricao__icontains='Pagamento').exists())

    def test_importa_porto_xlsx(self):
        caminho = AMOSTRAS / 'Fatura_Porto_Seguro_2026-09-28.xlsx'
        if not caminho.exists():
            self.skipTest('Arquivo de amostra Porto não encontrado')
        with caminho.open('rb') as fh:
            arquivo = SimpleUploadedFile(caminho.name, fh.read())
        criados, propagados, erros = importar_itens_arquivo(self.fatura, arquivo)
        self.assertEqual(erros, [])
        self.assertGreater(criados, 10)
        self.assertFalse(self.fatura.itens.filter(descricao__iexact='PAGAMENTO').exists())
        fla = self.fatura.itens.get(descricao='FLA DISTRIBUIDORA D')
        self.assertEqual(fla.parcela_atual, 9)
        self.assertEqual(fla.quantidade_parcelas, 10)
        # 9/10 → 1 parcela futura; Isolados 1/3 → 2; Anuidade 2/12 → 10; ML 1/10 → 9
        self.assertGreaterEqual(propagados, 1)
        isolados = self.fatura.itens.get(descricao='ISOLADOS.COM', valor=Decimal('593.28'))
        self.assertEqual(isolados.parcela_atual, 1)
        self.assertEqual(isolados.quantidade_parcelas, 3)
        anuidade = self.fatura.itens.get(descricao='ANUIDADE DIFERENCIADA')
        self.assertEqual(anuidade.parcela_atual, 2)
        self.assertEqual(anuidade.quantidade_parcelas, 12)
