from django.db import models
from portfolios.models import Portfolio
from decimal import Decimal

class CopyRelationship(models.Model):
    follower = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name='following'
    )
    leader = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name='followers'
    )
    allocated_cash = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    remaining_cash = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'leader')

    @property
    def invested(self):
        return self.allocated_cash - self.remaining_cash

    def __str__(self):
        return f"{self.follower} copies {self.leader}"



class CopyTradePnL(models.Model):
    follower = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="copy_pnls"
    )
    leader = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="leader_copy_pnls"
    )

    total_invested = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_realized_pnl = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("follower", "leader")

    def roi_percent(self):
        if self.total_invested <= 0:
            return Decimal("0.00")
        return (self.total_realized_pnl / self.total_invested) * 100