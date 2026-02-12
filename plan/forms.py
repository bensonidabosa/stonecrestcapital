from django import forms
from .models import Plan


class PlanForm(forms.ModelForm):

    class Meta:
        model = Plan
        fields = [
            "name",
            "plantype",
            "percent_increment",
            # "duration_days",
            "min_amount",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter plan name"
            }),

            "plantype": forms.Select(attrs={
                "class": "form-select"
            }),

            "percent_increment": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.0001",
                "placeholder": "0.5000"
            }),

            # "duration_days": forms.NumberInput(attrs={
            #     "class": "form-control",
            #     "placeholder": "Optional duration in days"
            # }),

            "min_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01"
            }),
        }
