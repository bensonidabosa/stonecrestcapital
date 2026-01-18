from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

from assets.models import Asset
from portfolios.models import Portfolio, Holding
from copytrading.models import CopyRelationship

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
        # elif total < 100:
        #     raise ValidationError(
        #         "Total allocation percentage is below 100% — strategy is under allocated"
        #         )


class PortfolioStrategy(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('STOPPED', 'Stopped'),
    )

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='strategy_allocations'
    )

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE
    )

    copy_relationship = models.ForeignKey(
        CopyRelationship,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="copied_strategies"
    )

    allocated_cash = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )

    activated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.strategy.name} ({self.allocated_cash})"


class StrategyHolding(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE
    )

    strategy_allocation = models.ForeignKey(
        PortfolioStrategy,
        on_delete=models.CASCADE,
        related_name='strategy_holdings'
    )

    holding = models.ForeignKey(
        Holding,
        on_delete=models.CASCADE,
        related_name='strategy_slices'
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4
    )

    average_price = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0")
    )

    class Meta:
        unique_together = ('strategy_allocation', 'asset')

