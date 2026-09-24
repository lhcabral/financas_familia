from django import forms

from despesas_basicas.models import DespesaBasica
from inicio.forms import RecorrenciaFormMixin


class DespesaBasicaForm(RecorrenciaFormMixin, forms.ModelForm):
    class Meta:
        model = DespesaBasica
        fields = ['ano', 'mes', 'descricao', 'valor', 'status', 'dia_vencimento', 'recorrente']
        widgets = {
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'recorrente': forms.CheckboxInput(attrs={'class': 'form-check'}),
        }

    field_order = [
        'ano', 'mes', 'descricao', 'valor', 'status',
        'dia_vencimento', 'recorrente', 'repetir_meses',
    ]
