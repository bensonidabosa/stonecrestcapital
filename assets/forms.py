from django import forms
from .models import Asset

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'name',
            'symbol',
            'asset_type',
            'price',
            'volatility',
            'annual_yield',
            'dividend_frequency',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter asset name'}),
            'symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter symbol'}),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'volatility': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'annual_yield': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dividend_frequency': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        asset_type = cleaned_data.get('asset_type')

        if asset_type != 'REIT':
            cleaned_data['annual_yield'] = None
            cleaned_data['dividend_frequency'] = None

        return cleaned_data
