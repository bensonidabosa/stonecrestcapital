from django.db import models
from django.core.exceptions import ValidationError

from assets.models import Asset
from portfolios.models import Portfolio

class Strategy(models.Model):
    RISK_LEVELS = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS
    )

    target_return_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Minimum expected annual return (%)"
    )

    target_return_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Maximum expected annual return (%)"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['risk_level', 'name']

    def clean(self):
        if self.target_return_min > self.target_return_max:
            raise ValidationError(
                "Minimum target return cannot be greater than maximum target return."
            )

    def asset_types(self):
        """
        Returns a set of human-readable asset types
        e.g. {'Stocks', 'REITs'}
        """
        return set(
            allocation.asset.get_asset_type_display()
            for allocation in self.allocations.select_related('asset')
        )

    def __str__(self):
        return self.name


class StrategyAllocation(models.Model):
    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    class Meta:
        unique_together = ('strategy', 'asset')

    def clean(self):
        total = sum(
            allocation.percentage
            for allocation in StrategyAllocation.objects.filter(
                strategy=self.strategy
            ).exclude(pk=self.pk)
        ) + self.percentage

        if total > 100:
            raise ValidationError(
                "Total allocation percentage cannot exceed 100%"
            )


class PortfolioStrategy(models.Model):
    portfolio = models.OneToOneField(
        Portfolio,
        on_delete=models.CASCADE
    )
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    activated_at = models.DateTimeField(auto_now_add=True)

