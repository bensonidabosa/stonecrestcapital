from decimal import Decimal
from django.db.models import Sum
from django.db import transaction
from portfolios.models import Holding
from .models import Trade
# from copytrading.services import mirror_trade
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

    # Safety: ensure we never spend more than available cash
    if cost > portfolio.cash_balance:
        raise ValueError(
            f"Cannot execute trade: portfolio balance {portfolio.cash_balance} is less than cost {cost}"
        )

    # Check against portfolio cash
    if portfolio.cash_balance < cost:
        return

    # Check against strategy allocation cash, if provided
    if strategy_allocation:
        if cost > strategy_allocation.remaining_cash:
            return

        # Only check copy_relationship if it exists
        if getattr(strategy_allocation, "copy_relationship", None):
            cr = strategy_allocation.copy_relationship
            if cr and cost > cr.remaining_cash:
                return

    with transaction.atomic():
        portfolio.cash_balance -= cost
        portfolio.save(update_fields=["cash_balance"])

        if strategy_allocation:
            strategy_allocation.remaining_cash -= cost
            strategy_allocation.save(update_fields=["remaining_cash"])

            # Deduct from copy_relationship if it exists
            if getattr(strategy_allocation, "copy_relationship", None):
                cr = strategy_allocation.copy_relationship
                if cr:
                    cr.remaining_cash -= cost
                    cr.save(update_fields=["remaining_cash"])

        holding, _ = Holding.objects.get_or_create(
            portfolio=portfolio,
            asset=asset,
            defaults={
                "quantity": Decimal("0"),
                "average_price": price,
            }
        )

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

        proceeds = quantity * price

        # 1️⃣ Reduce strategy holding
        sh.quantity -= quantity
        if sh.quantity <= 0:
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
            # Compute total quantity from all strategy holdings
            total_qty = StrategyHolding.objects.filter(
                portfolio=portfolio,
                asset=asset
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')

            holding.quantity = total_qty

            if holding.quantity <= 0:
                holding.delete()
            else:
                holding.save(update_fields=["quantity"])
        except Holding.DoesNotExist:
            pass

        # 4️⃣ Record trade
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.SELL,
            quantity=quantity,
            price=price,
            note=note,
        )
