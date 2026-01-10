from django.db import models
from django.contrib.auth.models import User

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    cash_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Portfolio"


class Strategy(models.Model):
    STRATEGY_TYPES = (
        ('growth', 'Growth'),
        ('income', 'Income / REIT'),
        ('copy', 'Copy Trading'),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=STRATEGY_TYPES)
    risk_level = models.IntegerField()
    rebalance_frequency_days = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserStrategy(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    allocation_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('portfolio', 'strategy')


class Asset(models.Model):
    ASSET_TYPES = (
        ('stock', 'Stock'),
        ('etf', 'ETF'),
        ('reit', 'REIT'),
    )

    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES)
    current_price = models.DecimalField(max_digits=20, decimal_places=4)

    def __str__(self):
        return self.symbol


class StrategyAsset(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    target_weight = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('strategy', 'asset')


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    avg_price = models.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        unique_together = ('portfolio', 'asset')


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('dividend', 'Dividend'),
    )

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    quantity = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Trader(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    performance_score = models.DecimalField(max_digits=6, decimal_places=2)


class TraderPosition(models.Model):
    trader = models.ForeignKey(Trader, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    allocation_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('trader', 'asset')


class Dividend(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    payout_rate = models.DecimalField(max_digits=10, decimal_places=4)
    payout_frequency_days = models.IntegerField()
    last_paid = models.DateTimeField(null=True, blank=True)


# User
# └── Portfolio
#     ├── UserStrategies (allocations)
#     ├── Positions (assets owned)
#     ├── Transactions
#     └── Performance Metrics (calculated)
