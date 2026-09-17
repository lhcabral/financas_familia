from django import forms

from despesas_basicas.models import DespesaBasica


class DespesaBasicaForm(forms.ModelForm):
    class Meta:
        model = DespesaBasica
        fields = ['ano', 'mes', 'descricao', 'valor', 'status']
        widgets = {
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
