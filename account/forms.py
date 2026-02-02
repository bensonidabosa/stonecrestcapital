from django import forms
from .models import User
from django_countries.widgets import CountrySelectWidget
from django_countries import countries


class AdminCustomerEditForm(forms.ModelForm):

    country = forms.ChoiceField(
        choices=[('', 'Select country')] + list(countries),
        widget=CountrySelectWidget(attrs={'class': 'form-control'}),
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "nick_name",
            "email",
            "address",
            "state",
            "country",
            "zipcode",
            "is_active",
            "can_be_copied",
        ]

        labels = {
            'nick_name': 'Username',
            'zipcode': 'Zip / Postal Code',
        }

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter full name"
            }),
            "nick_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter username"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Enter email"
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Enter address",
                "rows": 3
            }),
            "state": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter state"
            }),
            "country": CountrySelectWidget(attrs={
                "class": "form-control"
            }),
            "zipcode": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter zip code"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
            "can_be_copied": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }
