from decimal import Decimal
from django.db import transaction
from portfolios.models import Holding
from .models import Trade

def execute_buy(portfolio, asset, quantity):
    price = asset.price
    cost = price * quantity

    if portfolio.cash_balance < cost:
        raise ValueError("Insufficient cash")

    with transaction.atomic():
        portfolio.cash_balance -= cost
        portfolio.save(update_fields=['cash_balance'])

        holding, created = Holding.objects.get_or_create(
            portfolio=portfolio,
            asset=asset,
            defaults={
                'quantity': quantity,
                'average_price': price
            }
        )

        if not created:
            total_cost = (
                holding.quantity * holding.average_price
            ) + cost

            new_quantity = holding.quantity + quantity
            holding.average_price = total_cost / new_quantity
            holding.quantity = new_quantity
            holding.save()

        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.BUY,
            quantity=quantity,
            price=price
        )


def execute_sell(portfolio, asset, quantity):
    holding = Holding.objects.get(
        portfolio=portfolio,
        asset=asset
    )

    if holding.quantity < quantity:
        raise ValueError("Not enough quantity to sell")

    price = asset.price
    proceeds = price * quantity

    with transaction.atomic():
        holding.quantity -= quantity

        if holding.quantity == 0:
            holding.delete()
        else:
            holding.save(update_fields=['quantity'])

        portfolio.cash_balance += proceeds
        portfolio.save(update_fields=['cash_balance'])

        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.SELL,
            quantity=quantity,
            price=price
        )
