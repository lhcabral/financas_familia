from django import forms

from cartoes.models import Cartao, Fatura, ItemFatura


class CartaoForm(forms.ModelForm):
    class Meta:
        model = Cartao
        fields = ['nome', 'titular']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'titular': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FaturaForm(forms.ModelForm):
    class Meta:
        model = Fatura
        fields = ['cartao', 'ano', 'mes', 'status']
        widgets = {
            'cartao': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ItemFaturaForm(forms.ModelForm):
    class Meta:
        model = ItemFatura
        fields = ['descricao', 'valor']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
