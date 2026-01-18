from decimal import Decimal
from django.db import transaction
from portfolios.models import Portfolio, PortfolioSnapshot, Holding, RebalanceLog, DividendLog
from strategies.models import PortfolioStrategy, StrategyHolding
from trading.models import Trade
from trading.services import execute_sell
from copytrading.utils import is_copy_trading

def calculate_portfolio_value(portfolio):
    holdings_value = sum(
        h.market_value() for h in portfolio.holdings.all()
    )
    return portfolio.cash_balance + holdings_value


def calculate_holdings_value(portfolio):
    return sum(
        h.market_value() for h in portfolio.holdings.all()
    )

def rebalance_portfolio(portfolio):
    """
    Rebalance a single portfolio based on its assigned strategy
    """
    # 🔒 HARD LOCK
    if is_copy_trading(portfolio):
        return  # silently skip
    try:
        portfolio_strategy = PortfolioStrategy.objects.select_related(
            'strategy'
        ).get(portfolio=portfolio)
    except PortfolioStrategy.DoesNotExist:
        return  # portfolio has no strategy, skip

    strategy = portfolio_strategy.strategy
    total_value = portfolio.total_value()

    for allocation in strategy.allocations.select_related('asset'):
        target_value = (
            Decimal(allocation.percentage) / Decimal('100')
        ) * total_value

        holding, _ = Holding.objects.get_or_create(
            portfolio=portfolio,
            asset=allocation.asset,
            defaults={'quantity': 0}
        )

        current_value = holding.market_value()
        difference = target_value - current_value

        # Ignore very small drift
        if abs(difference) < Decimal('1.00'):
            continue

        if difference > 0:
            amount_bought = holding.buy_value(difference)
            if amount_bought > 0 and holding.asset.price is not None:
                Trade.objects.create(
                    portfolio=portfolio,
                    asset=holding.asset,
                    trade_type=Trade.REBALANCE,
                    quantity=amount_bought,
                    price=holding.asset.price,
                    note=f"Rebalance BUY to target {allocation.percentage}%"
                )
        else:
            amount_sold = holding.sell_value(abs(difference))
            if amount_sold > 0 and holding.asset.price is not None:
                Trade.objects.create(
                    portfolio=portfolio,
                    asset=holding.asset,
                    trade_type=Trade.REBALANCE,
                    quantity=amount_sold,
                    price=holding.asset.price,
                    note=f"Rebalance SELL to target {allocation.percentage}%"
                )

    # Optional: log a high-level rebalance
    RebalanceLog.objects.create(
        portfolio=portfolio,
        strategy=strategy,
        notes="Automated strategy rebalance"
    )


def pay_reit_dividends():
    reit_holdings = Holding.objects.filter(
        asset__asset_type='REIT',
        quantity__gt=0
    ).select_related('asset', 'portfolio')

    for holding in reit_holdings:
        asset = holding.asset

        if not asset.annual_yield:
            continue

        # Determine period yield
        if asset.dividend_frequency == 'MONTHLY':
            period_yield = asset.annual_yield / Decimal('12')
        else:
            period_yield = asset.annual_yield / Decimal('4')

        # Calculate dividend
        dividend_amount = holding.market_value() * period_yield / Decimal('100')

        if dividend_amount <= 0:
            continue

        # Add to portfolio cash
        portfolio = holding.portfolio
        portfolio.cash_balance += dividend_amount
        portfolio.save(update_fields=['cash_balance'])

        # Log Dividend
        DividendLog.objects.create(
            portfolio=portfolio,
            asset=asset,
            amount=dividend_amount
        )

        # ✅ Add Trade/Audit entry
        Trade.objects.create(
            portfolio=portfolio,
            asset=asset,
            trade_type=Trade.DIVIDEND,
            quantity=0,
            price=dividend_amount,
            note=f"{asset.symbol} dividend payout"
        )


def take_daily_snapshots():
    portfolios = Portfolio.objects.all()

    for portfolio in portfolios:
        PortfolioSnapshot.objects.create(
            portfolio=portfolio,
            total_value=portfolio.total_value(),
            cash_balance=portfolio.cash_balance
        )


# def unwind_portfolio(portfolio):
#     for holding in portfolio.holdings.select_related('asset'):
#         price = holding.asset.price

#         if price is None or price <= 0:
#             continue  # Skip selling invalid-priced assets

#         if holding.quantity > 0:
#             holding.sell_value(holding.market_value())
    
#     portfolio.holdings.filter(quantity=0).delete()

# def unwind_portfolio(portfolio):
#     """
#     Sell all holdings in the portfolio and register trades.
#     Used when stopping a strategy.
#     """
#     for holding in portfolio.holdings.select_related('asset'):
#         price = holding.asset.price

#         if price is None or price <= 0:
#             continue  # Skip invalid-priced assets

#         if holding.quantity > 0:
#             # Sell the full market value using execute_sell so a Trade is created
#             execute_sell(
#                 portfolio=portfolio,
#                 asset=holding.asset,
#                 quantity=holding.quantity,
#                 note="Strategy liquidation"
#             )

#     # Clean up holdings with zero quantity (though execute_sell deletes automatically)
#     portfolio.holdings.filter(quantity=0).delete()


# def unwind_strategy_holdings(portfolio, strategy_allocation):
#     """
#     Sell all holdings linked to a specific strategy allocation and register trades.
#     """
#     # Assuming we have a way to track which holdings came from which strategy allocation.
#     # For now, let's assume all holdings belong to this strategy allocation.
#     for holding in portfolio.holdings.select_related('asset'):
#         price = holding.asset.price
#         if price is None or price <= 0:
#             continue

#         if holding.quantity > 0:
#             execute_sell(
#                 portfolio=portfolio,
#                 asset=holding.asset,
#                 quantity=holding.quantity,
#                 note=f"Strategy ({strategy_allocation.strategy.name}) liquidation"
#             )

#     portfolio.holdings.filter(quantity=0).delete()

def unwind_strategy_holdings(portfolio, strategy_allocation):
    """
    Sell all holdings associated with a specific strategy allocation
    """
    holdings = StrategyHolding.objects.filter(
        strategy_allocation=strategy_allocation
    ).select_related('holding', 'asset')  # correct select_related

    for sh in holdings:
        holding = sh.holding
        asset = sh.asset
        price = asset.price

        if price is None or sh.quantity <= 0:
            continue

        execute_sell(
            portfolio=portfolio,
            asset=asset,
            quantity=sh.quantity,
            strategy_allocation=strategy_allocation,
            note=f"Liquidating strategy: {strategy_allocation.strategy.name}"
        )


    # Remove empty strategy holdings
    holdings.filter(quantity__lte=0).delete()


def unwind_copy_strategy_holdings(strategy_allocation):
    """
    Sell all holdings associated with a specific strategy allocation
    and return total cash realized.
    """
    portfolio = strategy_allocation.portfolio
    total_returned_cash = Decimal("0")

    holdings = StrategyHolding.objects.filter(
        strategy_allocation=strategy_allocation
    ).select_related("holding", "asset")

    for sh in holdings:
        asset = sh.asset
        quantity = sh.quantity
        price = asset.price

        if quantity <= 0 or price is None:
            continue

        proceeds = quantity * price

        execute_sell(
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            strategy_allocation=strategy_allocation,
            note=f"Liquidating strategy: {strategy_allocation.strategy.name}"
        )

        total_returned_cash += proceeds

    # Cleanup empty strategy holdings
    StrategyHolding.objects.filter(
        strategy_allocation=strategy_allocation,
        quantity__lte=0
    ).delete()

    return total_returned_cash



def unwind_portfolio(portfolio):
    """
    Liquidate all active strategies for a portfolio.
    Useful for stopping all strategies.
    """
    active_strategies = portfolio.strategy_allocations.filter(status='ACTIVE')
    for sa in active_strategies:
        unwind_strategy_holdings(portfolio, sa)
        sa.status = 'STOPPED'
        sa.save(update_fields=['status'])


def liquidate_portfolio(portfolio):
    """
    Sell all holdings in a portfolio
    """
    for holding in portfolio.holdings.select_related('asset'):
        if holding.quantity > 0:
            execute_sell(
                portfolio=portfolio,
                asset=holding.asset,
                quantity=holding.quantity,
                note="Copy trading liquidation"
            )
    # Step 3 — snapshot
    PortfolioSnapshot.objects.create(
        portfolio=portfolio,
        total_value=portfolio.total_value(),
        cash_balance=portfolio.cash_balance
    )






