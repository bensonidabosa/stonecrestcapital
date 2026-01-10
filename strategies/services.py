from decimal import Decimal
from trading.services import execute_buy

def execute_strategy(portfolio, strategy):
    allocations = strategy.allocations.all()
    cash = portfolio.cash_balance

    for allocation in allocations:
        amount_to_invest = (
            allocation.percentage / Decimal('100')
        ) * cash

        asset = allocation.asset
        price = asset.price

        quantity = amount_to_invest / price

        if quantity > 0:
            execute_buy(
                portfolio=portfolio,
                asset=asset,
                quantity=quantity
            )
