import re
from datetime import time

from django import forms

from backup.models import DIAS_SEMANA, AgendamentoBackup

HORARIO = re.compile(r'^(\d{1,2})[:h](\d{2})$')


class AgendamentoBackupForm(forms.ModelForm):
    dias = forms.TypedMultipleChoiceField(
        label='Dias da semana',
        choices=DIAS_SEMANA,
        coerce=int,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dias-semana'}),
    )

    class Meta:
        model = AgendamentoBackup
        fields = ['dias', 'horarios', 'retencao_dias', 'ativo']
        widgets = {
            'horarios': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '02:00, 14:00'}),
            'retencao_dias': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'horarios': 'Um ou mais horários no formato HH:MM, separados por vírgula.',
            'retencao_dias': 'Os backups deste agendamento mais antigos que isso são apagados e dão lugar aos novos.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['dias'] = self.instance.dias
            self.initial['horarios'] = self.instance.horarios_rotulo

    def clean_horarios(self):
        horarios = set()
        for texto in self.cleaned_data['horarios'].replace(';', ',').split(','):
            texto = texto.strip().lower()
            if not texto:
                continue
            encontrado = HORARIO.match(texto)
            hora, minuto = (int(parte) for parte in encontrado.groups()) if encontrado else (99, 99)
            if hora > 23 or minuto > 59:
                raise forms.ValidationError(f'Horário inválido: "{texto}". Use HH:MM, por exemplo 02:30.')
            horarios.add(time(hora, minuto))
        if not horarios:
            raise forms.ValidationError('Informe pelo menos um horário.')
        return ','.join(h.strftime('%H:%M') for h in sorted(horarios))

    def save(self, commit=True):
        self.instance.dias_semana = ','.join(str(dia) for dia in sorted(self.cleaned_data['dias']))
        return super().save(commit)


class ImportarBackupForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo .sql',
        widget=forms.ClearableFileInput(attrs={'accept': '.sql'}),
    )
    confirmar = forms.BooleanField(
        label='Entendo que todos os dados atuais serão substituídos pelos do arquivo.',
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        if not arquivo.name.lower().endswith('.sql'):
            raise forms.ValidationError('Envie um arquivo com extensão .sql.')
        return arquivo
