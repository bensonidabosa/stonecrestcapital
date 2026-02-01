from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal, ROUND_DOWN
from django.db import transaction
import logging

from strategies.models import PortfolioStrategy
from .models import CopyRelationship
from .services import copy_leader_strategies_to_follower

logger = logging.getLogger("copytrading.signal")
MIN_CASH_THRESHOLD = Decimal("200")

@receiver(post_save, sender=PortfolioStrategy)
def auto_copy_new_strategy(sender, instance, created, **kwargs):
    """
    When a leader creates a new strategy allocation,
    allocate to followers using their remaining copy cash.
    """
    # Only trigger for true leader strategies
    if not created or instance.copy_relationship_id is not None:
        return

    leader_portfolio = instance.portfolio

    logger.info(
        "[SIGNAL] New leader strategy created | leader=%s strategy=%s",
        leader_portfolio.id,
        instance.strategy.name
    )

    active_relations = CopyRelationship.objects.filter(
        leader=leader_portfolio,
        is_active=True
    ).select_related("follower")

    for relation in active_relations:
        follower = relation.follower
        remaining_cash = relation.remaining_cash

        logger.info(
            "[CHECK] follower=%s remaining_cash=%s",
            follower.id,
            remaining_cash
        )

        # Check allocation feasibility (20% rule)
        allocatable_cash = (remaining_cash * Decimal("0.2")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        if allocatable_cash < MIN_CASH_THRESHOLD:
            logger.info(
                "[SKIP] follower=%s allocatable_cash=%s below threshold=%s",
                follower.id,
                allocatable_cash,
                MIN_CASH_THRESHOLD
            )
            # Skip this follower only
            continue

        logger.info(
            "[ALLOCATE] follower=%s strategy=%s allocatable_cash=%s",
            follower.id,
            instance.strategy.name,
            allocatable_cash
        )

        copy_leader_strategies_to_follower(
            leader_portfolio=leader_portfolio,
            follower_portfolio=follower,
            relation=relation,
            buy_percent=Decimal("0.2"),
            specific_strategy=instance.strategy,
            min_cash=MIN_CASH_THRESHOLD
        )


@receiver(post_delete, sender=PortfolioStrategy)
def propagate_strategy_delete_to_followers(sender, instance, **kwargs):
    """
    When a leader liquidates (deletes) a strategy,
    fully unwind and delete follower copies.
    """
    from portfolios.services import unwind_copy_strategy_holdings_for_copy
    import logging

    logger = logging.getLogger("trading.services")

    # Ignore deletes of copied strategies
    if instance.copy_relationship_id:
        return

    leader_portfolio = instance.portfolio
    strategy = instance.strategy

    relations = CopyRelationship.objects.filter(
        leader=leader_portfolio,
        is_active=True
    )

    for relation in relations:
        copied_strategies = PortfolioStrategy.objects.filter(
            copy_relationship=relation,
            strategy=strategy
        )

        for ps in copied_strategies:
            returned_cash = unwind_copy_strategy_holdings_for_copy(ps)

            relation.remaining_cash += returned_cash
            relation.save(update_fields=["remaining_cash"])

            logger.info(
                "[COPY LIQUIDATION] follower=%s strategy=%s returned=%s remaining_cash=%s",
                relation.follower_id,
                strategy.name,
                returned_cash,
                relation.remaining_cash
            )

# @receiver(post_save, sender=PortfolioStrategy)
# def propagate_strategy_stop_to_followers(sender, instance, **kwargs):
#     """
#     When a leader stops a strategy, stop only copied versions for followers.
#     Liquidate holdings, credit proceeds to remaining_cash, and delete the PortfolioStrategy.
#     """
#     from portfolios.services import unwind_copy_strategy_holdings_for_copy

#     # Only trigger if the leader stops a strategy
#     if instance.status != "STOPPED":
#         return

#     # Skip if this is a copy itself
#     if instance.copy_relationship_id:
#         return

#     leader_portfolio = instance.portfolio

#     # Get all active followers
#     active_followers = CopyRelationship.objects.filter(
#         leader=leader_portfolio,
#         is_active=True
#     ).select_related("follower")

#     for relation in active_followers:
#         follower = relation.follower

#         # Find the copied strategy for this follower
#         copied_strategies = PortfolioStrategy.objects.filter(
#             copy_relationship=relation,
#             strategy=instance.strategy,
#             status="ACTIVE"
#         )

#         for ps in copied_strategies:
#             # Liquidate follower strategy and credit remaining_cash
#             total_returned = unwind_copy_strategy_holdings_for_copy(ps)

#             # Add to copy relationship remaining_cash
#             relation.remaining_cash += total_returned
#             relation.save(update_fields=["remaining_cash"])

#             logger.info(
#                 "[COPY STRATEGY STOP] Follower %s strategy %s liquidated, credited %s to remaining_cash=%s",
#                 follower.id,
#                 ps.strategy.name,
#                 total_returned,
#                 relation.remaining_cash
#             )

