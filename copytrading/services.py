from decimal import Decimal, ROUND_DOWN
from trading.models import Trade
import logging

from .models import CopyRelationship
from copytrading.models import CopyTradePnL
from trading.models import Trade
from strategies.models import PortfolioStrategy
from portfolios.services import unwind_copy_strategy_holdings

logger = logging.getLogger("copytrading.services")
MIN_CASH_THRESHOLD = Decimal("1000")  # Minimum allocation per strategy

def copy_leader_strategies_to_follower(
    leader_portfolio,
    follower_portfolio,
    allocated_cash,
    relation,
    buy_percent=Decimal("0.2"),
    specific_strategy=None,
    min_cash=Decimal("100")
):
    from strategies.services import execute_copy_strategy
    from strategies.models import PortfolioStrategy

    leader_strategies = leader_portfolio.strategy_allocations.filter(status="ACTIVE")
    if specific_strategy:
        leader_strategies = leader_strategies.filter(strategy=specific_strategy)

    if not leader_strategies.exists() or allocated_cash <= 0:
        logger.info("No strategies to copy or allocated cash is zero")
        return

    remaining_cash = Decimal(allocated_cash)
    logger.info(f"Starting copy: allocated_cash={allocated_cash}, remaining_cash={remaining_cash}")

    for leader_ps in leader_strategies:
        if remaining_cash < MIN_CASH_THRESHOLD:
            logger.info(f"Remaining cash {remaining_cash} below MIN_CASH_THRESHOLD, stopping allocation completely")
            break

        strategy_cash = (remaining_cash * Decimal(buy_percent)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        if strategy_cash < MIN_CASH_THRESHOLD:
            logger.info(f"Strategy cash {strategy_cash} below MIN_CASH_THRESHOLD, skipping {leader_ps.strategy.name}")
            continue

        follower_ps, created = PortfolioStrategy.objects.get_or_create(
            portfolio=follower_portfolio,
            strategy=leader_ps.strategy,
            copy_relationship=relation,
            defaults={
                "allocated_cash": strategy_cash,
                "remaining_cash": strategy_cash,
                "status": "ACTIVE"
            }
        )

        if not created:
            # Existing strategy: only update allocated_cash if needed, do NOT reset remaining_cash
            logger.info(f"Existing follower strategy {leader_ps.strategy.name}, allocated_cash={follower_ps.allocated_cash}, remaining_cash={follower_ps.remaining_cash}")

        # Execute strategy allocation
        logger.info(f"Executing copy strategy for {leader_ps.strategy.name}, remaining_cash={follower_ps.remaining_cash}")
        execute_copy_strategy(portfolio=follower_portfolio, strategy_allocation=follower_ps)

        # Deduct allocated cash from local remaining cash
        remaining_cash -= strategy_cash
        logger.info(f"Remaining cash after allocating to {leader_ps.strategy.name}: {remaining_cash}")



def check_follower_strategy_health(follower_portfolio):
    """
    Check all follower strategies and stop any that have depleted allocated cash.
    """
    for ps in follower_portfolio.strategy_allocations.filter(status='ACTIVE'):
        if ps.allocated_cash <= 0 or ps.portfolio.cash_balance <= 0:
            # Stop strategy safely
            ps.status = 'STOPPED'
            ps.save(update_fields=['status'])

            # Liquidate any holdings from this strategy
            from portfolios.services import unwind_strategy_holdings
            unwind_strategy_holdings(follower_portfolio, ps)


def stop_copying_and_unwind(follower_portfolio, leader_portfolio):
    """
    Stop copy trading and unwind only copied strategies.
    """

    try:
        relation = CopyRelationship.objects.get(
            follower=follower_portfolio,
            leader=leader_portfolio,
            is_active=True
        )
    except CopyRelationship.DoesNotExist:
        return

    copied_strategies = relation.copied_strategies.filter(status="ACTIVE")

    for ps in copied_strategies:
        # Sell all holdings (cash returned via execute_sell)
        unwind_copy_strategy_holdings(ps)

        # Fully close strategy
        ps.remaining_cash = Decimal("0")
        ps.status = "STOPPED"
        ps.save(update_fields=["remaining_cash", "status"])

    # Disable relationship
    relation.remaining_cash = Decimal("0")
    relation.is_active = False
    relation.save(update_fields=["remaining_cash", "is_active"])



