from django import forms
from .models import Transaction
from portfolios.models import Portfolio

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['portfolio', 'transaction_type', 'amount', 'note']

        widgets = {
            'portfolio': forms.Select(attrs={
                'placeholder': 'Select Portfolio',
                'class': 'form-control'
            }),
            'transaction_type': forms.Select(attrs={
                'placeholder': 'Select Transaction Type',
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'placeholder': 'Enter amount',
                'class': 'form-control'
            }),
            'note': forms.Textarea(attrs={
                'placeholder': 'Enter note (optional)',
                'class': 'form-control',
                'rows': 3
            }),
        }
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['portfolio'].queryset = Portfolio.objects.exclude(user__is_staff=True)

        # Pre-select Deposit
        self.fields['transaction_type'].initial = 'Deposit'

        if user:
            self.fields['portfolio'].queryset = self.fields['portfolio'].queryset.exclude(user=user)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

