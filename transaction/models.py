from django.db import models
from decimal import Decimal\

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('Deposit', 'Deposit'),
        ('Withdraw', 'Withdraw'),
        ('DIVIDEND', 'Dividend'),
        ('REBALANCE', 'Rebalance'),
        # ('Copy', 'Copy Pay'),
    ]

    portfolio = models.ForeignKey('portfolios.Portfolio', on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} {self.asset} {self.amount}"
