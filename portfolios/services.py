from decimal import Decimal

from portfolios.models import Portfolio, PortfolioSnapshot, Holding, RebalanceLog, DividendLog
from strategies.models import PortfolioStrategy
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


def unwind_portfolio(portfolio):
    for holding in portfolio.holdings.select_related('asset'):
        price = holding.asset.price

        if price is None or price <= 0:
            continue  # Skip selling invalid-priced assets

        if holding.quantity > 0:
            holding.sell_value(holding.market_value())
    
    portfolio.holdings.filter(quantity=0).delete()


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






