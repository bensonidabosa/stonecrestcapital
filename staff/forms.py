from django import forms
from django.utils import timezone

from transaction.models import Transaction
from plan.models import OrderPlan



class StaffTransactionForm(forms.ModelForm):
    ACTION_CHOICES = (
        ("fund", "Fund Account"),
        ("debit", "Debit Account"),
    )

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect,
        initial="fund",
        required=True,
    )

    timestamp = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
            },
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
        ],
    )

    class Meta:
        model = Transaction
        exclude = ("transaction_type", "balance")

        widgets = {
            "portfolio": forms.Select(attrs={"class": "form-select"}),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "coin": forms.Select(attrs={"class": "form-select"}),
            "destination_bank": forms.TextInput(attrs={"class": "form-control"}),
            "account_number": forms.TextInput(attrs={"class": "form-control"}),
            "wallet_id": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["action"].widget.attrs.update(
            {"class": "form-check-input"}
        )

        for field in self.fields.values():
            if isinstance(field.widget, forms.RadioSelect):
                continue

            css = field.widget.attrs.get("class", "")
            if "form-control" not in css and "form-select" not in css:
                field.widget.attrs["class"] = "form-control"


class OrderPlanUpdateForm(forms.ModelForm):
    start_at = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
            },
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ],
    )

    class Meta:
        model = OrderPlan
        fields = [
            "yield_percent",
            "start_at",
        ]

        widgets = {
            "yield_percent": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.0001",
                    "min": "0",
                }
            ),
        }