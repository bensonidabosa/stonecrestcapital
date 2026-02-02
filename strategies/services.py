from decimal import Decimal, ROUND_DOWN
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import PortfolioStrategy, StrategyHolding
from trading.services import execute_buy
from portfolios.models import Portfolio, PortfolioSnapshot
from portfolios.services import unwind_portfolio, unwind_strategy_holdings
from trading.models import Trade
from copytrading.utils import is_copy_trading

def execute_strategy(portfolio, strategy_allocation, max_cash=None):
    strategy = strategy_allocation.strategy

    # Determine cash to use
    if hasattr(strategy_allocation, 'copy_relationship') and strategy_allocation.copy_relationship:
        total_cash = min(strategy_allocation.remaining_cash,
                         strategy_allocation.copy_relationship.remaining_cash)
    else:
        total_cash = strategy_allocation.remaining_cash
        print(total_cash)
        print(strategy_allocation.allocated_cash)

    # If a max_cash is passed (e.g., from copy_leader_strategies_to_follower), respect it
    if max_cash is not None:
        total_cash = min(total_cash, max_cash)

    if total_cash <= 0:
        return

    for allocation in strategy.allocations.select_related('asset'):
        if allocation.asset.price <= 0:
            continue

        target_cash = (allocation.percentage / 100) * total_cash
        quantity = target_cash / allocation.asset.price

        execute_buy(
            portfolio=portfolio,
            asset=allocation.asset,
            quantity=quantity,
            strategy_allocation=strategy_allocation,
            note=f"Strategy allocation: {strategy.name}"
        )


def strategy_average_return(strategy):
    portfolios = Portfolio.objects.filter(
        strategy_allocations__strategy=strategy
    )

    returns = [
        p.return_percentage()
        for p in portfolios
        if p.initial_value() and p.initial_value() >= 1000
    ]

    return sum(returns) / len(returns) if returns else 0


def switch_strategy(portfolio, new_strategy):
    """
    Safely switch a portfolio from one strategy to another
    """
    # 🔒 HARD LOCK
    if is_copy_trading(portfolio):
        raise ValueError("Stop copy trading before selecting a strategy")
    
    # STEP 14.3 — Safety guard (EDGE CASE)
    if portfolio.holdings.filter(quantity__gt=0).exists():
        unwind_portfolio(portfolio)

    # Remove old strategy link if it exists
    PortfolioStrategy.objects.filter(portfolio=portfolio).delete()

    # Link new strategy
    portfolio_strategy = PortfolioStrategy.objects.create(
        portfolio=portfolio,
        strategy=new_strategy
    )

    # Apply new strategy (copy trading)
    execute_strategy(portfolio, new_strategy)

    # New baseline snapshot
    PortfolioSnapshot.objects.create(
        portfolio=portfolio,
        total_value=portfolio.total_value(),
        cash_balance=portfolio.cash_balance
    )

    # ✅ Add Trade/Audit log for strategy switch
    Trade.objects.create(
        portfolio=portfolio,
        trade_type=Trade.SWITCH,
        quantity=0,
        price=portfolio.total_value(),
        note=f"Switched to strategy: {new_strategy.name}"
    )

    return portfolio_strategy


def liquidate_strategy(portfolio, strategy_allocation=None):
    """
    Sell all holdings for a given strategy allocation (or all active strategies),
    record a snapshot, and remove the PortfolioStrategy record(s) after liquidation.
    """
    with transaction.atomic():
        if strategy_allocation:
            # Sell only holdings linked to this strategy allocation
            unwind_strategy_holdings(portfolio, strategy_allocation)
            
            # Delete the strategy allocation after liquidation
            strategy_allocation.delete()
        else:
            # Sell all holdings for all active strategies
            for ps in portfolio.strategy_allocations.filter(status='ACTIVE'):
                unwind_strategy_holdings(portfolio, ps)
                ps.delete()

        # Record a snapshot after liquidation
        PortfolioSnapshot.objects.create(
            portfolio=portfolio,
            total_value=portfolio.total_value(),
            cash_balance=portfolio.cash_balance
        )


def calculate_strategy_metrics(strategy_allocation):
    """
    Returns value, cost, pnl, roi for a strategy
    """
    holdings = StrategyHolding.objects.filter(
        strategy_allocation=strategy_allocation
    ).select_related("asset")

    total_cost = Decimal("0")
    current_value = Decimal("0")

    for sh in holdings:
        cost = sh.quantity * sh.average_price
        value = sh.quantity * sh.asset.price

        total_cost += cost
        current_value += value

    pnl = current_value - total_cost
    roi = (pnl / total_cost * 100) if total_cost > 0 else Decimal("0")

    return {
        "current_value": current_value,
        "total_cost": total_cost,
        "pnl": pnl,
        "roi": round(roi, 2),
    }


def execute_copy_strategy(portfolio, strategy_allocation):
    """
    Buy holdings for copy trading without affecting normal strategies.
    Uses remaining cash of follower strategy only.
    """
    strategy = strategy_allocation.strategy
    total_cash = Decimal(strategy_allocation.remaining_cash)

    if total_cash <= 0:
        return

    for allocation in strategy.allocations.select_related('asset'):
        asset_price = Decimal(allocation.asset.price)
        if asset_price <= 0:
            continue

        # Cash to allocate for this asset
        target_cash = (total_cash * Decimal(allocation.percentage) / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        if target_cash <= 0:
            continue

        # Determine quantity to buy
        quantity = (target_cash / asset_price).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
        if quantity <= 0:
            continue

        # Execute actual buy
        execute_buy(
            portfolio=portfolio,
            asset=allocation.asset,
            quantity=quantity,
            strategy_allocation=strategy_allocation,
            note=f"Copy strategy allocation: {strategy.name}"
        )



