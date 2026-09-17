from django import forms

from filhos.models import DespesaFilho, Filho


class DespesaFilhoForm(forms.ModelForm):
    class Meta:
        model = DespesaFilho
        fields = ['filho', 'ano', 'mes', 'descricao', 'valor', 'status']
        widgets = {
            'filho': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class FilhoForm(forms.ModelForm):
    class Meta:
        model = Filho
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }
