from decimal import Decimal, ROUND_DOWN
import logging
from django.db import transaction

from .models import CopyRelationship
from copytrading.models import CopyTradePnL
from trading.models import Trade
from strategies.models import PortfolioStrategy
from portfolios.services import unwind_copy_strategy_holdings

logger = logging.getLogger("copytrading.services")

def copy_leader_strategies_to_follower(
    leader_portfolio,
    follower_portfolio,
    relation,
    buy_percent=Decimal("0.2"),
    specific_strategy=None,
    min_cash=Decimal("200")
):
    from strategies.services import execute_copy_strategy
    from strategies.models import PortfolioStrategy

    logger.info(
        "[COPY START] follower=%s leader=%s remaining_cash=%s buy_percent=%s min_cash=%s",
        follower_portfolio.id,
        leader_portfolio.id,
        relation.remaining_cash,
        buy_percent,
        min_cash
    )

    leader_strategies = leader_portfolio.strategy_allocations.filter(status="ACTIVE")
    if specific_strategy:
        leader_strategies = leader_strategies.filter(strategy=specific_strategy)
        logger.info(
            "[FILTER] Copying specific strategy=%s",
            specific_strategy.name
        )

    remaining_cash = relation.remaining_cash

    if not leader_strategies.exists():
        logger.info("[STOP] No active leader strategies to copy")
        return

    if remaining_cash < min_cash:
        logger.info(
            "[STOP] Remaining cash %s below min_cash %s",
            remaining_cash,
            min_cash
        )
        return

    for idx, leader_ps in enumerate(leader_strategies, start=1):
        logger.info(
            "[STRATEGY %s] %s | remaining_cash=%s",
            idx,
            leader_ps.strategy.name,
            remaining_cash
        )

        if remaining_cash < min_cash:
            logger.info(
                "[BREAK] remaining_cash %s < min_cash %s",
                remaining_cash,
                min_cash
            )
            break

        strategy_cash = (remaining_cash * buy_percent).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        logger.info(
            "[CALC] %s × %s = %s",
            remaining_cash,
            buy_percent,
            strategy_cash
        )

        if strategy_cash < min_cash:
            logger.info(
                "[BREAK] strategy_cash %s < min_cash %s → stop allocating",
                strategy_cash,
                min_cash
            )
            break

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

        if created:
            logger.info(
                "[CREATE] Follower strategy %s allocated_cash=%s",
                leader_ps.strategy.name,
                strategy_cash
            )
            execute_copy_strategy(
                portfolio=follower_portfolio,
                strategy_allocation=follower_ps
            )
            logger.info(
                "[EXECUTE] Strategy %s executed",
                leader_ps.strategy.name
            )
        else:
            logger.info(
                "[SKIP] Strategy %s already exists (allocated_cash=%s, remaining_cash=%s)",
                leader_ps.strategy.name,
                follower_ps.allocated_cash,
                follower_ps.remaining_cash
            )

        # 🔑 update state
        remaining_cash -= strategy_cash
        relation.remaining_cash = remaining_cash
        relation.save(update_fields=["remaining_cash"])

        logger.info(
            "[DEDUCT] Deducted=%s new_remaining_cash=%s",
            strategy_cash,
            remaining_cash
        )

    logger.info(
        "[COPY END] follower=%s leader=%s final_remaining_cash=%s",
        follower_portfolio.id,
        leader_portfolio.id,
        relation.remaining_cash
    )


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
    Stop copy trading, unwind copied strategies, credit remaining cash, and delete the copy relationship.
    Cash from sold assets is returned via unwind_copy_strategy_holdings().
    """
    try:
        relation = CopyRelationship.objects.get(
            follower=follower_portfolio,
            leader=leader_portfolio
        )
    except CopyRelationship.DoesNotExist:
        logger.info(f"No active copy relationship for follower={follower_portfolio.id}, leader={leader_portfolio.id}")
        return

    copied_strategies = relation.copied_strategies.filter(status="ACTIVE")
    logger.info(
        f"Stopping copy: follower={follower_portfolio.id}, leader={leader_portfolio.id}, active_strategies={copied_strategies.count()}"
    )

    with transaction.atomic():
        total_returned_cash = Decimal("0")

        for ps in copied_strategies:
            logger.info(f"Unwinding strategy={ps.strategy.name} for follower={follower_portfolio.id}")
            
            # Sell all holdings (cash credited via unwind function)
            unwind_copy_strategy_holdings(ps)

            # Add any remaining cash in the strategy allocation to the total to return
            total_returned_cash += ps.remaining_cash

            # Close strategy bookkeeping
            ps.remaining_cash = Decimal("0")
            ps.status = "STOPPED"
            ps.save(update_fields=["remaining_cash", "status"])

            logger.info(f"Strategy={ps.strategy.name} stopped. Remaining cash={ps.remaining_cash}")

        # Credit follower with any leftover remaining_cash in strategies + relation
        remaining_from_relation = relation.remaining_cash
        total_returned_cash += remaining_from_relation

        if total_returned_cash > 0:
            follower_portfolio.cash_balance += total_returned_cash
            follower_portfolio.save(update_fields=["cash_balance"])
            logger.info(f"Credited follower={follower_portfolio.id} with remaining cash={total_returned_cash}")

        # Remove strategy allocations
        copied_strategies.delete()
        logger.info(f"All copied strategies deleted for follower={follower_portfolio.id}")

        # Delete the copy relationship (session ended)
        relation.delete()
        logger.info(f"Copy relationship deleted for follower={follower_portfolio.id}, leader={leader_portfolio.id}")






