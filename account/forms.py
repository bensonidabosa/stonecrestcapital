from django import forms
from .models import User


class AdminCustomerEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "full_name",
            "nick_name",
            "email",
            "is_active",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "nick_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }