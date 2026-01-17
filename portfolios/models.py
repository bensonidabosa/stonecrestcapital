from django.conf import settings
from django.db import models
from decimal import Decimal
from django.db.models import Sum, F, DecimalField, ExpressionWrapper

from assets.models import Asset

User = settings.AUTH_USER_MODEL

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cash_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('1000000.00')  # virtual money
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def total_holding_value(self):
        holdings_value = sum(
            h.market_value() for h in self.holdings.all()
        )
        return holdings_value
    
    def total_value(self):
        holdings_value = sum(
            h.market_value() for h in self.holdings.all()
        )
        return self.cash_balance + holdings_value

    def __str__(self):
        return f"{self.user} Portfolio"
    
    def initial_value(self):
        first = self.snapshots.order_by('created_at').first()
        return first.total_value if first else self.cash_balance

    def current_value(self):
        return self.total_value()

    def total_return(self):
        return self.current_value() - self.initial_value()
    
    def return_percentage(self):
        initial = self.initial_value()

        if not initial or initial <= 0:
            return 0

        return ((self.current_value() - initial) / initial) * 100

    # def return_percentage(self):
    #     initial = self.initial_value()
    #     if initial == 0:
    #         return 0
    #     return (self.total_return() / initial) * 100
    

class Holding(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='holdings'
    )
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0')
    )

    average_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )

    class Meta:
        unique_together = ('portfolio', 'asset')

    @property
    def total_quantity(self):
        return self.strategy_slices.aggregate(
            total=models.Sum('quantity')
        )['total'] or Decimal('0')

    def market_value(self):
        return self.asset.price * self.total_quantity
    
    def cost_basis(self):
        return self.average_price * self.total_quantity

    def unrealized_pnl(self):
        return self.market_value() - self.cost_basis()

    def unrealized_pnl_percent(self):
        cost = self.cost_basis()
        if cost == 0:
            return Decimal('0')
        return (self.unrealized_pnl() / cost) * Decimal('100')



class RebalanceLog(models.Model):
    portfolio = models.ForeignKey(
        'Portfolio',
        on_delete=models.CASCADE,
        related_name='rebalances'
    )
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE
    )
    executed_at = models.DateTimeField(auto_now_add=True)

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Rebalance {self.portfolio.id} @ {self.executed_at}"


class DividendLog(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='dividends'
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset.symbol} dividend {self.amount}"


class PortfolioSnapshot(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='snapshots'
    )
    total_value = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )
    cash_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.portfolio.id} @ {self.created_at}"
    

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('DIVIDEND', 'Dividend'),
        ('REBALANCE', 'Rebalance'),
        ('SWITCH', 'Strategy Switch'),
    ]

    portfolio = models.ForeignKey('Portfolio', on_delete=models.CASCADE, related_name='transactions')
    asset = models.ForeignKey('assets.Asset', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'))
    price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    total_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} {self.asset} {self.total_value}"
