from django import forms

from inicio.constants import ANO_PADRAO, MESES
from inicio.models import Receita


class ReceitaForm(forms.ModelForm):
    class Meta:
        model = Receita
        fields = ['ano', 'mes', 'fonte', 'valor', 'observacao']
        widgets = {
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'fonte': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacao': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FiltroAnoMesForm(forms.Form):
    ano = forms.IntegerField(
        initial=ANO_PADRAO,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
    )
    mes = forms.TypedChoiceField(
        coerce=int,
        required=False,
        choices=[('', 'Todos os meses')] + list(MESES),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
