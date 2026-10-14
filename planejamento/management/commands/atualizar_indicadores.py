from django.core.management.base import BaseCommand

from planejamento import banco_central


class Command(BaseCommand):
    help = 'Baixa Selic, CDI, IPCA e poupança da API do Banco Central.'

    def handle(self, *args, **options):
        erros = banco_central.atualizar_indicadores(forcar=True)
        for erro in erros:
            self.stderr.write(self.style.ERROR(erro))
        for item in banco_central.indicadores().values():
            if item['valor'] is None:
                continue
            self.stdout.write(f'{item["nome"]}: {item["valor"]}% {item["unidade"]} ({item["data_referencia"]:%d/%m/%Y})')
        if not erros:
            self.stdout.write(self.style.SUCCESS('Indicadores atualizados.'))
