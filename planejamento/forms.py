from django import forms

from planejamento.models import PerfilFinanceiro


class PerfilFinanceiroForm(forms.ModelForm):
    class Meta:
        model = PerfilFinanceiro
        fields = ['reserva_atual', 'meses_reserva']
        widgets = {
            'reserva_atual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'meses_reserva': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 24}),
        }

    def clean_meses_reserva(self):
        meses = self.cleaned_data['meses_reserva']
        if not 1 <= meses <= 24:
            raise forms.ValidationError('Use entre 1 e 24 meses.')
        return meses

    def clean_reserva_atual(self):
        valor = self.cleaned_data['reserva_atual']
        if valor < 0:
            raise forms.ValidationError('A reserva não pode ser negativa.')
        return valor
