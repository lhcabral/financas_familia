from django import forms

from inicio.constants import ANO_PADRAO, MESES
from inicio.models import Receita


class RecorrenciaFormMixin(forms.Form):
    repetir_meses = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=24,
        label='Repetir nos próximos meses',
        help_text='Cria o mesmo lançamento à frente. Deixe em branco para só este mês.',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 24,
            'placeholder': 'Ex.: 11',
        }),
    )


class ReceitaForm(RecorrenciaFormMixin, forms.ModelForm):
    class Meta:
        model = Receita
        fields = [
            'ano', 'mes', 'fonte', 'valor', 'observacao',
            'status', 'dia_vencimento', 'recorrente',
        ]
        widgets = {
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'fonte': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacao': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'recorrente': forms.CheckboxInput(attrs={'class': 'form-check'}),
        }

    field_order = [
        'ano', 'mes', 'fonte', 'valor', 'observacao',
        'status', 'dia_vencimento', 'recorrente', 'repetir_meses',
    ]


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
