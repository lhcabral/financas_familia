from datetime import datetime, time, timedelta

from django.db import models
from django.utils import timezone

DIAS_SEMANA = [
    (0, 'Segunda'),
    (1, 'Terça'),
    (2, 'Quarta'),
    (3, 'Quinta'),
    (4, 'Sexta'),
    (5, 'Sábado'),
    (6, 'Domingo'),
]

RETENCAO_CHOICES = [
    (1, '1 dia'),
    (7, '1 semana'),
    (15, '15 dias'),
    (30, '1 mês'),
    (90, '3 meses'),
    (180, '6 meses'),
    (365, '1 ano'),
]


class AgendamentoBackup(models.Model):
    dias_semana = models.CharField(max_length=20, verbose_name='Dias da semana')
    horarios = models.CharField(max_length=200, verbose_name='Horários')
    retencao_dias = models.PositiveSmallIntegerField(
        choices=RETENCAO_CHOICES,
        default=7,
        verbose_name='Substituir backups com mais de',
    )
    ativo = models.BooleanField(default=True)
    ultima_execucao = models.DateTimeField(null=True, blank=True, verbose_name='Última execução')
    ultimo_erro = models.TextField(blank=True, verbose_name='Último erro')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pk']
        verbose_name = 'Agendamento de backup'
        verbose_name_plural = 'Agendamentos de backup'

    def __str__(self):
        return f'{self.dias_rotulo} às {self.horarios_rotulo}'

    @property
    def dias(self):
        return sorted(int(dia) for dia in self.dias_semana.split(',') if dia.strip())

    @property
    def lista_horarios(self):
        return sorted(time.fromisoformat(h.strip()) for h in self.horarios.split(',') if h.strip())

    @property
    def dias_rotulo(self):
        dias = self.dias
        if len(dias) == 7:
            return 'Todos os dias'
        nomes = dict(DIAS_SEMANA)
        return ', '.join(nomes[dia][:3].lower() for dia in dias)

    @property
    def horarios_rotulo(self):
        return ', '.join(h.strftime('%H:%M') for h in self.lista_horarios)

    @property
    def prefixo_arquivo(self):
        return f'agendado-{self.pk}_'

    def proxima_execucao(self, depois_de=None):
        depois_de = depois_de or timezone.now()
        dias, horarios = set(self.dias), self.lista_horarios
        if not dias or not horarios:
            return None
        inicio = timezone.localtime(depois_de).date()
        for deslocamento in range(8):
            data = inicio + timedelta(days=deslocamento)
            if data.weekday() not in dias:
                continue
            for horario in horarios:
                momento = timezone.make_aware(datetime.combine(data, horario))
                if momento > depois_de:
                    return momento
        return None

    def pendente(self, agora=None):
        agora = agora or timezone.now()
        referencia = max(filter(None, [self.ultima_execucao, self.atualizado_em]))
        prevista = self.proxima_execucao(referencia)
        return prevista is not None and prevista <= agora

    def reservar_execucao(self, agora):
        """Marca a execução só se nenhum outro processo chegou antes."""
        atualizados = AgendamentoBackup.objects.filter(
            pk=self.pk, ultima_execucao=self.ultima_execucao,
        ).update(ultima_execucao=agora)
        if atualizados:
            self.ultima_execucao = agora
        return bool(atualizados)
