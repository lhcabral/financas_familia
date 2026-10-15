from django.core.management.base import BaseCommand

from backup import servicos


class Command(BaseCommand):
    help = 'Gera os backups agendados cujo horário já chegou (para uso com cron).'

    def handle(self, *args, **options):
        for arquivo in servicos.executar_pendentes():
            self.stdout.write(self.style.SUCCESS(f'Backup gerado: {arquivo}'))
