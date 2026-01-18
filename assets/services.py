import random
from decimal import Decimal
from django.db import transaction
from .models import Asset

# Unified stimulation function
def stimulate_prices(direction='both'):
    assets = Asset.objects.all()
    with transaction.atomic():
        for asset in assets:
            if direction == 'positive':
                change_percent = Decimal(random.uniform(0, float(asset.volatility)))
            elif direction == 'negative':
                change_percent = Decimal(random.uniform(-float(asset.volatility), 0))
            else:  # both
                change_percent = Decimal(random.uniform(-float(asset.volatility), float(asset.volatility)))

            multiplier = Decimal('1.00') + (change_percent / Decimal('100'))
            new_price = asset.price * multiplier
            asset.price = max(new_price, Decimal('1.00'))
            asset.save(update_fields=['price'])
            

# def simulate_price_changes():
#     assets = Asset.objects.all()

#     with transaction.atomic():
#         for asset in assets:
#             change_percent = Decimal(
#                 random.uniform(
#                     -float(asset.volatility),
#                     float(asset.volatility)
#                 )
#             )

#             multiplier = Decimal('1.00') + (change_percent / Decimal('100'))
#             new_price = asset.price * multiplier

#             asset.price = max(new_price, Decimal('1.00'))
#             asset.save(update_fields=['price'])


# # Function to simulate only positive changes
# def simulate_positive_price_changes():
#     assets = Asset.objects.all()
#     with transaction.atomic():
#         for asset in assets:
#             change_percent = Decimal(
#                 random.uniform(
#                     0.0,  # only positive
#                     float(asset.volatility)
#                 )
#             )
#             multiplier = Decimal('1.00') + (change_percent / Decimal('100'))
#             new_price = asset.price * multiplier
#             asset.price = max(new_price, Decimal('1.00'))
#             asset.save(update_fields=['price'])


# # Function to simulate only negative changes
# def simulate_negative_price_changes():
#     assets = Asset.objects.all()
#     with transaction.atomic():
#         for asset in assets:
#             change_percent = Decimal(
#                 random.uniform(
#                     -float(asset.volatility),  # only negative
#                     0.0
#                 )
#             )
#             multiplier = Decimal('1.00') + (change_percent / Decimal('100'))
#             new_price = asset.price * multiplier
#             asset.price = max(new_price, Decimal('1.00'))
#             asset.save(update_fields=['price'])

