from django import forms
from .models import Transaction
from portfolios.models import Portfolio

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'portfolio',
            'transaction_type',
            'payment_method',
            'currency',
            'amount',
            'note',
            'status',
        ]

        widgets = {
            'portfolio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount'
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter note (optional)'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['portfolio'].queryset = Portfolio.objects.exclude(user__is_staff=True)

        # Optional field (matches null=True, blank=True)
        self.fields['payment_method'].required = False
        self.fields['currency'].required = False

        # Pre-select Deposit
        self.fields['transaction_type'].initial = 'DEPOSIT'
        self.fields['currency'].initial = 'USD'

        if user:
            self.fields['portfolio'].queryset = self.fields['portfolio'].queryset.exclude(user=user)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount
    

class CustomerTransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'payment_method',
            'currency',
            'amount',
            'note',
            'destination_bank',
            'account_number',
            'wallet_id',
            'coin_type',
        ]

        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter note (optional)'}),
            'destination_bank': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Destination Bank'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account Number'}),
            'coin_type': forms.Select(attrs={'class': 'form-select'}),
            'wallet_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wallet ID'}),
        }

    def __init__(self, *args, transaction_type=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['currency'].required = False
        self.fields['currency'].initial = 'USD'

        # make all conditional fields optional by default
        self.fields['destination_bank'].required = False
        self.fields['account_number'].required = False
        self.fields['wallet_id'].required = False
        self.fields['coin_type'].required = False

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get("payment_method")

        if payment_method == "WIRE":
            if not cleaned_data.get("destination_bank"):
                self.add_error("destination_bank", "Destination bank is required for wire transfer.")
            if not cleaned_data.get("account_number"):
                self.add_error("account_number", "Account number is required for wire transfer.")

        if payment_method == "CRYPTO":
            if not cleaned_data.get("wallet_id"):
                self.add_error("wallet_id", "Wallet ID is required for crypto withdrawals.")
            if not cleaned_data.get("coin_type"):
                self.add_error("coin_type", "Coin type is required for crypto withdrawals.")

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

