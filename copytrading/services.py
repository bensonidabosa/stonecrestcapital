from decimal import Decimal, ROUND_DOWN
from trading.models import Trade
from .models import CopyRelationship

from copytrading.models import CopyTradePnL
from trading.models import Trade
from strategies.models import PortfolioStrategy
from portfolios.services import unwind_copy_strategy_holdings

# def copy_leader_strategies_to_follower(
#     leader_portfolio,
#     follower_portfolio,
#     allocated_cash,
#     relation,
#     specific_strategy=None
# ):
#     """
#     Copy leader strategies to follower.
#     - If specific_strategy is None → copy ALL active strategies
#     - If specific_strategy is provided → copy ONLY that strategy
#     """
#     from strategies.models import PortfolioStrategy
#     from strategies.services import execute_strategy

#     # Get all active leader strategies
#     leader_strategies = leader_portfolio.strategy_allocations.filter(status="ACTIVE")

#     if specific_strategy:
#         leader_strategies = leader_strategies.filter(strategy=specific_strategy)

#     if not leader_strategies.exists():
#         return

#     total_leader_cash = sum(ps.allocated_cash for ps in leader_strategies)
#     if total_leader_cash <= 0:
#         return

#     for leader_ps in leader_strategies:
#         # Proportional allocation for follower
#         weight = leader_ps.allocated_cash / total_leader_cash
#         follower_cash = weight * allocated_cash

#         if follower_cash <= 0:
#             continue

#         # Get or create follower strategy
#         follower_ps, created = PortfolioStrategy.objects.get_or_create(
#             portfolio=follower_portfolio,
#             strategy=leader_ps.strategy,
#             copy_relationship=relation,
#             defaults={
#                 "allocated_cash": follower_cash,
#                 "remaining_cash": follower_cash,
#                 "status": "ACTIVE",
#             },
#         )

#         if not created:
#             # Update allocated_cash but keep remaining_cash proportional
#             spent = follower_ps.allocated_cash - follower_ps.remaining_cash
#             follower_ps.allocated_cash = follower_cash
#             follower_ps.remaining_cash = max(follower_cash - spent, 0)
#             follower_ps.status = "ACTIVE"
#             follower_ps.save(update_fields=["allocated_cash", "remaining_cash", "status"])

#         # Execute strategy using only remaining_cash
#         execute_strategy(
#             portfolio=follower_portfolio,
#             strategy_allocation=follower_ps,
#             max_cash=follower_ps.remaining_cash,  # NEW: limit to remaining_cash
#         )


MIN_CASH_THRESHOLD = Decimal("1000")  # stop allocating if remaining cash < 1k

def copy_leader_strategies_to_follower(
    leader_portfolio,
    follower_portfolio,
    allocated_cash,
    relation,
    buy_percent=Decimal("0.2"),  # fraction of remaining cash per leader strategy
    specific_strategy=None,
    min_cash=1000 
):
    """
    Copy leader strategies to follower portfolio.
    - buy_percent: fraction of remaining follower cash to allocate per leader strategy
    - Stops when remaining cash < MIN_CASH_THRESHOLD
    """
    from strategies.services import execute_copy_strategy

    leader_strategies = leader_portfolio.strategy_allocations.filter(status="ACTIVE")
    if specific_strategy:
        leader_strategies = leader_strategies.filter(strategy=specific_strategy)

    if not leader_strategies.exists() or allocated_cash <= 0:
        return

    remaining_cash = Decimal(allocated_cash)

    for leader_ps in leader_strategies:
        if remaining_cash < MIN_CASH_THRESHOLD:
            break

        # Amount to allocate for this strategy
        strategy_cash = (remaining_cash * Decimal(buy_percent)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        if strategy_cash < MIN_CASH_THRESHOLD:
            continue

        # Create or update follower strategy allocation
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
            # Keep track of spent cash
            spent = follower_ps.allocated_cash - follower_ps.remaining_cash
            follower_ps.allocated_cash = strategy_cash
            follower_ps.remaining_cash = max(strategy_cash - spent, Decimal("0"))
            follower_ps.status = "ACTIVE"
            follower_ps.save(update_fields=["allocated_cash", "remaining_cash", "status"])

        # Execute the strategy allocation
        execute_copy_strategy(
            portfolio=follower_portfolio,
            strategy_allocation=follower_ps,
        )

        remaining_cash -= strategy_cash



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

    total_returned_cash = Decimal("0")

    copied_strategies = relation.copied_strategies.filter(
        status="ACTIVE"
    )

    for ps in copied_strategies:
        # Unwind holdings
        returned_cash = unwind_copy_strategy_holdings(ps)
        total_returned_cash += returned_cash

        ps.status = "STOPPED"
        ps.save(update_fields=["status"])

    # Return allocated cash back to follower
    follower_portfolio.cash_balance += total_returned_cash
    follower_portfolio.save(update_fields=["cash_balance"])

    # Disable relationship
    relation.is_active = False
    relation.save(update_fields=["is_active"])

