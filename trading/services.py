import logging
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction

from portfolios.models import Holding
from .models import Trade
from strategies.models import StrategyHolding

logger = logging.getLogger(__name__)

MIN_CASH_THRESHOLD = Decimal('400')

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

        # ✅ NEW: enforce MIN_CASH_THRESHOLD
        if strategy_allocation.remaining_cash < MIN_CASH_THRESHOLD:
            logger.info(
                f"Remaining cash {strategy_allocation.remaining_cash} below MIN_CASH_THRESHOLD {MIN_CASH_THRESHOLD}, skipping buy"
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
    logger.info(f"The final remaining cash is {strategy_allocation.remaining_cash if strategy_allocation else 'N/A'}")


def execute_sell(portfolio, asset, quantity, strategy_allocation=None, note=""):
    """
    Sell a given quantity of an asset under a strategy allocation.
    Cash is credited to both portfolio and strategy_allocation (if provided).
    """
    price = asset.price
    if price is None or price <= 0 or quantity <= 0:
        logger.warning(
            f"[SELL SKIP] Invalid sell parameters: asset={asset}, price={price}, quantity={quantity}"
        )
        return Decimal("0")

    quantity = Decimal(quantity)
    price = Decimal(price)
    proceeds = (quantity * price).quantize(Decimal("0.01"))

    with transaction.atomic():
        try:
            sh = StrategyHolding.objects.get(
                portfolio=portfolio,
                strategy_allocation=strategy_allocation,
                asset=asset
            )
        except StrategyHolding.DoesNotExist:
            logger.warning(
                f"[SELL SKIP] StrategyHolding not found: portfolio={portfolio.id}, "
                f"strategy_allocation={getattr(strategy_allocation, 'id', None)}, asset={asset}"
            )
            return Decimal("0")

        if quantity > sh.quantity:
            logger.info(
                f"[SELL ADJUST] Requested quantity {quantity} exceeds holding {sh.quantity}, adjusting"
            )
            quantity = sh.quantity

        # 1️⃣ Reduce strategy holding
        sh.quantity -= quantity
        if sh.quantity <= 0:
            sh.delete()
            logger.info(
                f"[HOLDING DELETE] StrategyHolding deleted: portfolio={portfolio.id}, asset={asset}"
            )
        else:
            sh.save(update_fields=["quantity"])
            logger.info(
                f"[HOLDING UPDATE] StrategyHolding updated: portfolio={portfolio.id}, asset={asset}, remaining={sh.quantity}"
            )

        # 2️⃣ Credit portfolio cash
        portfolio.cash_balance += proceeds
        portfolio.save(update_fields=["cash_balance"])
        logger.info(
            f"[CASH CREDIT] Portfolio {portfolio.id} credited {proceeds} from selling {quantity} {asset}"
        )

        # 3️⃣ Credit strategy allocation remaining cash
        if strategy_allocation:
            strategy_allocation.remaining_cash += proceeds
            strategy_allocation.save(update_fields=["remaining_cash"])
            logger.info(
                f"[STRATEGY CASH CREDIT] StrategyAllocation {strategy_allocation.id} credited {proceeds} remaining_cash={strategy_allocation.remaining_cash}"
            )

        # 4️⃣ Sync combined holding
        total_qty = StrategyHolding.objects.filter(
            portfolio=portfolio,
            asset=asset
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")

        if total_qty <= 0:
            Holding.objects.filter(portfolio=portfolio, asset=asset).delete()
            logger.info(f"[HOLDING DELETE] Combined holding deleted: portfolio={portfolio.id}, asset={asset}")
        else:
            Holding.objects.update_or_create(
                portfolio=portfolio,
                asset=asset,
                defaults={"quantity": total_qty}
            )
            logger.info(f"[HOLDING UPDATE] Combined holding updated: portfolio={portfolio.id}, asset={asset}, total_quantity={total_qty}")

        # 5️⃣ Record trade
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.SELL,
            quantity=quantity,
            price=price,
            note=note,
        )
        logger.info(
            f"[TRADE RECORD] SELL: portfolio={portfolio.id}, asset={asset}, quantity={quantity}, price={price}, note='{note}'"
        )

    return proceeds


def execute_copy_sell(
    strategy_allocation,
    asset,
    quantity,
    note=""
):
    """
    Sell a given quantity of an asset for a copy-trading strategy.
    Proceeds go to strategy_allocation.remaining_cash only (portfolio cash untouched).
    """
    price = asset.price
    if price is None or price <= 0 or quantity <= 0:
        logger.warning(f"[COPY SELL SKIP] Invalid sell: asset={asset}, price={price}, quantity={quantity}")
        return Decimal("0")

    quantity = Decimal(quantity)
    price = Decimal(price)
    proceeds = (quantity * price).quantize(Decimal("0.01"))

    portfolio = strategy_allocation.portfolio

    with transaction.atomic():
        try:
            sh = StrategyHolding.objects.get(
                portfolio=portfolio,
                strategy_allocation=strategy_allocation,
                asset=asset
            )
        except StrategyHolding.DoesNotExist:
            logger.warning(f"[COPY SELL SKIP] StrategyHolding not found: asset={asset}")
            return Decimal("0")

        if quantity > sh.quantity:
            quantity = sh.quantity
            logger.info(f"[COPY SELL ADJUST] Quantity adjusted to holding: {quantity}")

        # Reduce strategy holding
        sh.quantity -= quantity
        if sh.quantity <= 0:
            sh.delete()
            logger.info(f"[COPY SELL] StrategyHolding deleted: {asset}")
        else:
            sh.save(update_fields=["quantity"])
            logger.info(f"[COPY SELL] StrategyHolding updated: {asset}, remaining={sh.quantity}")

        # Credit to strategy allocation remaining cash only
        strategy_allocation.remaining_cash += proceeds
        strategy_allocation.save(update_fields=["remaining_cash"])
        logger.info(f"[COPY SELL] Credited {proceeds} to strategy_allocation.remaining_cash={strategy_allocation.remaining_cash}")

        # Sync combined holding
        total_qty = StrategyHolding.objects.filter(
            portfolio=portfolio,
            asset=asset
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")

        if total_qty <= 0:
            Holding.objects.filter(portfolio=portfolio, asset=asset).delete()
        else:
            Holding.objects.update_or_create(
                portfolio=portfolio,
                asset=asset,
                defaults={"quantity": total_qty}
            )

        # Record trade (optional, can still track SELLs)
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.SELL,
            quantity=quantity,
            price=price,
            note=note
        )

    return proceeds
