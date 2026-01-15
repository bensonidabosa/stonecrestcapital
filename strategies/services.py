from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import PortfolioStrategy
from trading.services import execute_buy
from portfolios.models import Portfolio, PortfolioSnapshot
from portfolios.services import unwind_portfolio
from trading.models import Trade
from copytrading.utils import is_copy_trading

def execute_strategy(portfolio, strategy):
    allocations = strategy.allocations.select_related('asset')

    # 🔒 PRICE SAFETY CHECK
    for allocation in allocations:
        asset = allocation.asset
        if asset.price is None or asset.price <= 0:
            raise ValidationError(
                f"Asset price not available for {asset.symbol}. "
                "Please simulate prices first."
            )

    total_percentage = sum(a.percentage for a in allocations)
    if total_percentage > 100:
        raise ValidationError("Strategy allocations exceed 100%")

    cash = portfolio.cash_balance

    for allocation in allocations:
        amount_to_invest = (
            allocation.percentage / Decimal('100')
        ) * cash

        quantity = amount_to_invest / allocation.asset.price

        if quantity > 0:
            execute_buy(
                portfolio=portfolio,
                asset=allocation.asset,
                quantity=quantity
            )



def strategy_average_return(strategy):
    portfolios = Portfolio.objects.filter(
        portfoliostrategy__strategy=strategy
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


def liquidate_strategy(portfolio):
    """
    Exit strategy mode safely:
    - Sell all holdings
    - Convert to cash
    - Remove PortfolioStrategy
    """
    with transaction.atomic():
        # 1️⃣ Sell everything
        unwind_portfolio(portfolio)

        # 2️⃣ Remove strategy link
        PortfolioStrategy.objects.filter(portfolio=portfolio).delete()

