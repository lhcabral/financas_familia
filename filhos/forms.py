from django import forms

from filhos.models import DespesaFilho, Filho
from inicio.forms import RecorrenciaFormMixin


class DespesaFilhoForm(RecorrenciaFormMixin, forms.ModelForm):
    class Meta:
        model = DespesaFilho
        fields = ['filho', 'ano', 'mes', 'descricao', 'valor', 'status', 'dia_vencimento', 'recorrente']
        widgets = {
            'filho': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'recorrente': forms.CheckboxInput(attrs={'class': 'form-check'}),
        }

    field_order = [
        'filho', 'ano', 'mes', 'descricao', 'valor', 'status',
        'dia_vencimento', 'recorrente', 'repetir_meses',
    ]


class FilhoForm(forms.ModelForm):
    class Meta:
        model = Filho
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }
