from django.contrib import admin

from backup.models import AgendamentoBackup


@admin.register(AgendamentoBackup)
class AgendamentoBackupAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'retencao_dias', 'ativo', 'ultima_execucao']
    list_filter = ['ativo']
