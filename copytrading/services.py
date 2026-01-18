from decimal import Decimal
from trading.models import Trade
from .models import CopyRelationship

from copytrading.models import CopyTradePnL
from trading.models import Trade
from strategies.models import PortfolioStrategy
from portfolios.services import unwind_copy_strategy_holdings



# def copy_leader_strategies_to_follower(leader_portfolio, follower_portfolio, allocated_cash, relation, specific_strategy=None):
#     """
#     Copy all active leader strategies to the follower.
#     Each follower strategy receives cash proportionally.
#     """
#     from strategies.services import execute_strategy

#     active_strategies = leader_portfolio.strategy_allocations.filter(status='ACTIVE')
#     total_leader_cash = sum(ps.allocated_cash for ps in active_strategies)

#     if total_leader_cash <= 0:
#         return  # Nothing to copy

#     for leader_ps in active_strategies:
#         # Allocate proportional follower cash
#         follower_cash = (leader_ps.allocated_cash / total_leader_cash) * allocated_cash

#         # Create follower PortfolioStrategy
#         follower_ps, created = PortfolioStrategy.objects.get_or_create(
#             portfolio=follower_portfolio,
#             strategy=leader_ps.strategy,
#             status='ACTIVE',
#             copy_relationship=relation,
#             defaults={'allocated_cash': follower_cash}
#         )

#         if not created:
#             # If already exists (from previous copy), just update allocated cash
#             follower_ps.allocated_cash = follower_cash
#             follower_ps.status = 'ACTIVE'
#             follower_ps.save(update_fields=['allocated_cash', 'status'])

#         # Execute strategy for follower using their allocated cash
#         execute_strategy(
#             portfolio=follower_portfolio,
#             strategy_allocation=follower_ps
#         )

def copy_leader_strategies_to_follower(
    leader_portfolio,
    follower_portfolio,
    allocated_cash,
    relation,
    specific_strategy=None
):
    """
    Copy leader strategies to follower.
    - If specific_strategy is None → copy ALL active strategies
    - If specific_strategy is provided → copy ONLY that strategy
    """

    from strategies.models import PortfolioStrategy
    from strategies.services import execute_strategy

    leader_strategies = leader_portfolio.strategy_allocations.filter(
        status="ACTIVE"
    )

    # 🔹 THIS IS WHERE YOUR SNIPPET BELONGS
    if specific_strategy:
        leader_strategies = leader_strategies.filter(
            strategy=specific_strategy
        )

    if not leader_strategies.exists():
        return

    total_leader_cash = sum(
        ps.allocated_cash for ps in leader_strategies
    )

    if total_leader_cash <= 0:
        return

    for leader_ps in leader_strategies:
        # Proportional allocation
        weight = leader_ps.allocated_cash / total_leader_cash
        follower_cash = weight * allocated_cash

        if follower_cash <= 0:
            continue

        follower_ps, created = PortfolioStrategy.objects.get_or_create(
            portfolio=follower_portfolio,
            strategy=leader_ps.strategy,
            copy_relationship=relation,  # 🔐 CRITICAL
            defaults={
                "allocated_cash": follower_cash,
                "status": "ACTIVE",
            },
        )

        if not created:
            follower_ps.allocated_cash += follower_cash
            follower_ps.status = "ACTIVE"
            follower_ps.save(update_fields=["allocated_cash", "status"])

        execute_strategy(
            portfolio=follower_portfolio,
            strategy_allocation=follower_ps,
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

