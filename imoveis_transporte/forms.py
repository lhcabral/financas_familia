from django import forms

from imoveis_transporte.models import Consorcio, ParcelaConsorcio


class ConsorcioForm(forms.ModelForm):
    class Meta:
        model = Consorcio
        fields = ['nome', 'grupo', 'total_parcelas']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'grupo': forms.TextInput(attrs={'class': 'form-control'}),
            'total_parcelas': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ParcelaConsorcioForm(forms.ModelForm):
    class Meta:
        model = ParcelaConsorcio
        fields = [
            'consorcio', 'ano', 'mes', 'rotulo_parcela',
            'numero_parcela', 'valor', 'status',
        ]
        widgets = {
            'consorcio': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'rotulo_parcela': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '27/200'}),
            'numero_parcela': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
