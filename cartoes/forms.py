from django import forms

from cartoes.models import Cartao, Fatura, ItemFatura


class CartaoForm(forms.ModelForm):
    class Meta:
        model = Cartao
        fields = ['nome', 'titular', 'dia_vencimento']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'titular': forms.TextInput(attrs={'class': 'form-control'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
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
        fields = ['descricao', 'valor', 'quantidade_parcelas', 'parcela_atual']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantidade_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'parcela_atual': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not getattr(self.instance, 'pk', None):
            self.fields['quantidade_parcelas'].initial = self.fields['quantidade_parcelas'].initial or 1
            self.fields['parcela_atual'].initial = self.fields['parcela_atual'].initial or 1

    def clean(self):
        cleaned = super().clean()
        quantidade = cleaned.get('quantidade_parcelas') or 1
        atual = cleaned.get('parcela_atual') or 1
        cleaned['quantidade_parcelas'] = quantidade
        cleaned['parcela_atual'] = atual
        if atual > quantidade:
            self.add_error(
                'parcela_atual',
                'A parcela atual não pode ser maior que a quantidade de parcelas.',
            )
        return cleaned


class ImportarItensCSVForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo',
        help_text=(
            'CSV (Nubank, Bradesco ou simples) ou XLSX da Porto Seguro. '
            'Parcelas são detectadas e lançadas nos meses seguintes.'
        ),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xls,.xlsx,text/csv,application/vnd.ms-excel,'
                      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }),
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        nome = (arquivo.name or '').lower()
        if not nome.endswith(('.csv', '.xls', '.xlsx', '.xlsm')):
            raise forms.ValidationError('Envie um arquivo CSV ou XLS/XLSX.')
        if arquivo.size and arquivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('O arquivo deve ter no máximo 5 MB.')
        return arquivo
