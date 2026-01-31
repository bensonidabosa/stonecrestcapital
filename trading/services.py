import logging
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction

from portfolios.models import Holding
from .models import Trade
from strategies.models import StrategyHolding

logger = logging.getLogger(__name__)

def execute_buy(
    portfolio,
    asset,
    quantity,
    strategy_allocation=None,
    note=""
):
    price = asset.price
    if price is None or price <= 0 or quantity <= 0:
        logger.debug(f"Skipping buy: invalid price ({price}) or quantity ({quantity}) for {asset}")
        return

    cost = quantity * price

    # Safety: ensure we never spend more than available cash
    if cost > portfolio.cash_balance:
        logger.warning(
            f"Cannot execute trade: portfolio balance {portfolio.cash_balance} is less than cost {cost} for {asset}"
        )
        return

    # Check against strategy allocation cash, if provided
    if strategy_allocation:
        if getattr(strategy_allocation, "copy_relationship", None):
            cr = strategy_allocation.copy_relationship
            if cr and cost > cr.remaining_cash:
                logger.debug(
                    f"Skipping buy: copy_relationship remaining_cash {cr.remaining_cash} < cost {cost} for {asset}"
                )
                return
        else:
            if cost > strategy_allocation.remaining_cash:
                logger.debug(
                    f"Skipping buy: strategy_allocation remaining_cash {strategy_allocation.remaining_cash} < cost {cost} for {asset}"
                )
                return

    with transaction.atomic():
        # Deduct from strategy allocation only, not portfolio cash (already deducted on allocation)
        if strategy_allocation:
            strategy_allocation.remaining_cash -= cost
            strategy_allocation.save(update_fields=["remaining_cash"])

        holding, _ = Holding.objects.get_or_create(
            portfolio=portfolio,
            asset=asset,
            defaults={"quantity": Decimal("0"), "average_price": price},
        )

        if strategy_allocation:
            sh, _ = StrategyHolding.objects.get_or_create(
                portfolio=portfolio,
                strategy_allocation=strategy_allocation,
                asset=asset,
                holding=holding,
                defaults={"quantity": Decimal("0"), "average_price": price},
            )

            total_cost = (sh.quantity * sh.average_price) + cost
            sh.quantity += quantity
            sh.average_price = total_cost / sh.quantity
            sh.save(update_fields=["quantity", "average_price"])

        holding.quantity = holding.total_quantity
        holding.save(update_fields=["quantity"])

        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.BUY,
            quantity=quantity,
            price=price,
            note=note,
        )

        logger.info(f"Executed BUY: {quantity} of {asset} at {price} under {strategy_allocation}")
    logger.info(f"the final remaining cash is {strategy_allocation.remaining_cash}")



def execute_sell(
    portfolio,
    asset,
    quantity,
    strategy_allocation,
    note=""
):
    price = asset.price
    if price is None or price <= 0 or quantity <= 0:
        return

    quantity = Decimal(quantity)
    price = Decimal(price)

    with transaction.atomic():
        sh = StrategyHolding.objects.get(
            portfolio=portfolio,
            strategy_allocation=strategy_allocation,
            asset=asset
        )

        if quantity > sh.quantity:
            quantity = sh.quantity

        proceeds = (quantity * price).quantize(Decimal("0.01"))

        # 1️⃣ Reduce strategy holding
        sh.quantity -= quantity
        if sh.quantity <= 0:
            sh.delete()
        else:
            sh.save(update_fields=["quantity"])

        # 2️⃣ Credit portfolio cash
        portfolio.cash_balance += proceeds
        portfolio.save(update_fields=["cash_balance"])

        # 3️⃣ Sync combined holding
        total_qty = StrategyHolding.objects.filter(
            portfolio=portfolio,
            asset=asset
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")

        if total_qty <= 0:
            Holding.objects.filter(
                portfolio=portfolio,
                asset=asset
            ).delete()
        else:
            Holding.objects.update_or_create(
                portfolio=portfolio,
                asset=asset,
                defaults={"quantity": total_qty}
            )

        # 4️⃣ Record trade
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.SELL,
            quantity=quantity,
            price=price,
            note=note,
        )


# def execute_sell(
#     portfolio,
#     asset,
#     quantity,
#     strategy_allocation=None,
#     note=""
# ):
#     price = asset.price
#     if price is None or price <= 0 or quantity <= 0:
#         return

#     quantity = Decimal(quantity)
#     price = Decimal(price)

#     with transaction.atomic():
#         sh = StrategyHolding.objects.get(
#             portfolio=portfolio,
#             strategy_allocation=strategy_allocation,
#             asset=asset
#         )

#         if quantity > sh.quantity:
#             quantity = sh.quantity

#         proceeds = quantity * price

#         # 1️⃣ Reduce strategy holding
#         sh.quantity -= quantity
#         if sh.quantity <= 0:
#             sh.delete()
#         else:
#             sh.save(update_fields=["quantity"])

#         # 2️⃣ Credit cash
#         portfolio.cash_balance += proceeds
#         portfolio.save(update_fields=["cash_balance"])

#         # 3️⃣ Sync combined holding
#         try:
#             holding = Holding.objects.get(
#                 portfolio=portfolio,
#                 asset=asset
#             )
#             # Compute total quantity from all strategy holdings
#             total_qty = StrategyHolding.objects.filter(
#                 portfolio=portfolio,
#                 asset=asset
#             ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')

#             holding.quantity = total_qty

#             if holding.quantity <= 0:
#                 holding.delete()
#             else:
#                 holding.save(update_fields=["quantity"])
#         except Holding.DoesNotExist:
#             pass

#         # 4️⃣ Record trade
#         Trade.objects.create(
#             portfolio=portfolio,
#             asset=asset,
#             trade_type=Trade.SELL,
#             quantity=quantity,
#             price=price,
#             note=note,
#         )
