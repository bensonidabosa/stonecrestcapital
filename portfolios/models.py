from django.conf import settings
from django.db import models
from decimal import Decimal

User = settings.AUTH_USER_MODEL

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cash_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('1000000.00')  # virtual money
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} Portfolio"
