from decimal import Decimal
from django.db import transaction
from portfolios.models import Holding
from .models import Trade
from copytrading.services import mirror_trade
from strategies.models import StrategyHolding

def execute_buy(
    portfolio,
    asset,
    quantity,
    strategy_allocation=None,
    note=""
):
    price = asset.price
    if price is None or price <= 0 or quantity <= 0:
        return

    cost = quantity * price

    if portfolio.cash_balance < cost:
        raise ValueError("Insufficient cash")

    with transaction.atomic():
        # 1️⃣ Deduct cash ONCE
        portfolio.cash_balance -= cost
        portfolio.save(update_fields=["cash_balance"])

        # 2️⃣ Get or create combined holding
        holding, _ = Holding.objects.get_or_create(
            portfolio=portfolio,
            asset=asset,
            defaults={
                "quantity": Decimal("0"),
                "average_price": price,
            }
        )

        # 3️⃣ Strategy-level holding
        if strategy_allocation:
            sh, _ = StrategyHolding.objects.get_or_create(
                portfolio=portfolio,
                strategy_allocation=strategy_allocation,
                asset=asset,
                holding=holding,
                defaults={
                    "quantity": Decimal("0"),
                    "average_price": price,
                }
            )

            total_cost = (sh.quantity * sh.average_price) + cost
            sh.quantity += quantity
            sh.average_price = total_cost / sh.quantity
            sh.save(update_fields=["quantity", "average_price"])

        # 4️⃣ Sync combined holding quantity
        holding.quantity = holding.total_quantity
        holding.save(update_fields=["quantity"])

        # 5️⃣ Register trade
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.BUY,
            quantity=quantity,
            price=price,
            note=note,
        )

    mirror_trade(
        leader_portfolio=portfolio,
        asset=asset,
        trade_type=Trade.BUY,
        quantity=quantity
    )

# def execute_buy(
#     portfolio,
#     asset,
#     quantity,
#     strategy_allocation=None,
#     note=""
# ):
#     price = asset.price
#     cost = price * quantity

#     if cost <= 0:
#         return

#     if portfolio.cash_balance < cost:
#         raise ValueError("Insufficient cash")

#     with transaction.atomic():
#         # 1️⃣ Deduct cash ONCE
#         portfolio.cash_balance -= cost
#         portfolio.save(update_fields=['cash_balance'])

#         # 2️⃣ Update portfolio-level holding
#         holding, _ = Holding.objects.get_or_create(
#             portfolio=portfolio,
#             asset=asset,
#             defaults={
#                 'quantity': 0,
#                 'average_price': price
#             }
#         )

#         holding.quantity += quantity
#         holding.save(update_fields=['quantity'])

#         # 3️⃣ Update strategy-level holding
#         if strategy_allocation:
#             sh, _ = StrategyHolding.objects.get_or_create(
#                 portfolio=portfolio,
#                 strategy_allocation=strategy_allocation,
#                 asset=asset,
#                 holding=holding,
#                 defaults={'quantity': 0}
#             )
#             sh.quantity += quantity
#             sh.save(update_fields=['quantity'])

#         # 4️⃣ Register trade
#         Trade.objects.create(
#             portfolio=portfolio,
#             asset=asset,
#             trade_type=Trade.BUY,
#             quantity=quantity,
#             price=price,
#             note=note
#         )

#     mirror_trade(
#         leader_portfolio=portfolio,
#         asset=asset,
#         trade_type=Trade.BUY,
#         quantity=quantity
#     )


def execute_sell(
    portfolio,
    asset,
    quantity,
    strategy_allocation=None,
    note=""
):
    price = asset.price
    if price is None or price <= 0 or quantity <= 0:
        return

    with transaction.atomic():
        sh = StrategyHolding.objects.get(
            portfolio=portfolio,
            strategy_allocation=strategy_allocation,
            asset=asset
        )

        if quantity > sh.quantity:
            quantity = sh.quantity

        proceeds = quantity * price

        # 1️⃣ Reduce strategy holding
        sh.quantity -= quantity
        if sh.quantity == 0:
            sh.delete()
        else:
            sh.save(update_fields=["quantity"])

        # 2️⃣ Credit cash
        portfolio.cash_balance += proceeds
        portfolio.save(update_fields=["cash_balance"])

        # 3️⃣ Sync combined holding
        try:
            holding = Holding.objects.get(
                portfolio=portfolio,
                asset=asset
            )
            holding.quantity = holding.total_quantity

            if holding.quantity == 0:
                holding.delete()
            else:
                holding.save(update_fields=["quantity"])
        except Holding.DoesNotExist:
            pass

        # 4️⃣ Trade record
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.SELL,
            quantity=quantity,
            price=price,
            note=note,
        )

    # Mirror to followers if needed
    mirror_trade(leader_portfolio=portfolio, asset=asset, trade_type=Trade.SELL, quantity=quantity)


# def execute_sell(portfolio, asset, quantity, strategy_allocation=None, note=""):
#     price = asset.price
#     if price is None or quantity <= 0:
#         return Decimal('0')

#     cost = price * quantity

#     with transaction.atomic():
#         holding = Holding.objects.get(portfolio=portfolio, asset=asset)

#         if strategy_allocation:
#             sh = StrategyHolding.objects.get(
#                 strategy_allocation=strategy_allocation,
#                 holding=holding
#             )
#             if quantity > sh.quantity:
#                 quantity = sh.quantity
#                 cost = price * quantity
#             sh.quantity -= quantity
#             if sh.quantity == 0:
#                 sh.delete()
#             else:
#                 sh.save(update_fields=['quantity'])

#         # Update combined holding
#         holding.quantity = holding.total_quantity
#         if holding.quantity == 0:
#             holding.delete()
#         else:
#             holding.save(update_fields=['quantity'])

#         portfolio.cash_balance += cost
#         portfolio.save(update_fields=['cash_balance'])

#         # Record the trade
#         Trade.objects.create(
#             portfolio=portfolio,
#             asset=asset,
#             trade_type=Trade.SELL,
#             quantity=quantity,
#             price=price,
#             note=note
#         )

#     # Mirror to followers if needed
#     mirror_trade(leader_portfolio=portfolio, asset=asset, trade_type=Trade.SELL, quantity=quantity)
