from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError

class Asset(models.Model):
    ASSET_TYPES = (
        ('STOCK', 'Stock'),
        ('ETF', 'ETF'),
        ('REIT', 'REIT'),
    )

    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=20, unique=True)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('100.00')
    )

    volatility = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.50')
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # NEW (only meaningful for REITs)
    annual_yield = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Annual dividend yield (%)",
        null=True,
        blank=True
    )

    dividend_frequency = models.CharField(
        max_length=20,
        choices=(
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly'),
        ),
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['symbol']

    def clean(self):
        if self.asset_type != 'REIT':
            if self.annual_yield is not None or self.dividend_frequency is not None:
                raise ValidationError(
                    "Annual yield and dividend frequency are only applicable to REIT assets."
                )

    def __str__(self):
        return f"{self.symbol} ({self.asset_type})"
