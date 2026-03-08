from decimal import Decimal
from django.db import models


class CopyRelationship(models.Model):

    follower = models.ForeignKey(
        "customer.Portfolio",
        on_delete=models.CASCADE,
        related_name="following"
    )

    leader = models.ForeignKey(
        "customer.Portfolio",
        on_delete=models.CASCADE,
        related_name="followers"
    )

    allocated_cash = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00")
    )

    remaining_cash = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00")
    )

    trade_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00")  # 20%
    )

    min_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("800.00")
    )

    is_active = models.BooleanField(default=True)

    last_copied_orderplan = models.ForeignKey(
        "plan.OrderPlan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "leader")

    @property
    def invested(self):
        return self.allocated_cash - self.remaining_cash

    def can_copy_trade(self):
        return (
            self.is_active
            and self.remaining_cash >= self.min_balance
        )

    def trade_amount(self):
        """
        Amount used per copied trade
        """
        return self.remaining_cash * (self.trade_percentage / Decimal("100"))

    def __str__(self):
        return f"{self.follower} copies {self.leader}"
    

class CopyTrade(models.Model):

    relationship = models.ForeignKey(
        CopyRelationship,
        on_delete=models.CASCADE,
        related_name="copied_trades"
    )

    leader_orderplan = models.ForeignKey(
        "plan.OrderPlan",
        on_delete=models.CASCADE,
        related_name="leader_trades"
    )

    follower_orderplan = models.ForeignKey(
        "plan.OrderPlan",
        on_delete=models.CASCADE,
        related_name="follower_trades"
    )

    amount_used = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("relationship", "leader_orderplan")