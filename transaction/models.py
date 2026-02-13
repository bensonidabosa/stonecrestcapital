from django.db import models
from decimal import Decimal

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAW', 'Withdraw'),
        ('DIVIDEND', 'Dividend'),
        ('REBALANCE', 'Rebalance'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP'),
    ]

    PAYMENT_METHODS = [
        ('WIRE', 'Wire Transfer'),
        ('CRYPTO', 'Crypto'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESSFUL', 'Successful'),
        ('FAILED', 'Failed'),
    ]

    COIN_CHOICES = [
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('USDT', 'USDT'),
    ]

    portfolio = models.ForeignKey(
        'customer.Portfolio',
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        null=True,
        blank=True
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0')
    )
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0')
    )

    destination_bank = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    account_number = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    coin_type = models.CharField(
        max_length=10,
        choices=COIN_CHOICES,
        null=True,
        blank=True
    )
    wallet_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} - {self.payment_method} - {self.amount} ({self.status})"