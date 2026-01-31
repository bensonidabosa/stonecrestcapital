from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal, ROUND_DOWN
import logging

from strategies.models import PortfolioStrategy
from .models import CopyRelationship
from .services import copy_leader_strategies_to_follower


logger = logging.getLogger("copytrading.signal")
# MIN_CASH_THRESHOLD = Decimal("1000") 

# @receiver(post_save, sender=PortfolioStrategy)
# def auto_copy_new_strategy(sender, instance, created, **kwargs):
#     """
#     When a leader creates a new strategy allocation, copy it to all active followers.
#     Only allocate if the follower has enough remaining cash.
#     """
#     if not created or instance.copy_relationship_id is not None:
#         return  # Only trigger for true new leader strategies

#     leader_portfolio = instance.portfolio

#     # Get all active followers
#     active_followers = CopyRelationship.objects.filter(
#         leader=leader_portfolio,
#         is_active=True
#     ).select_related("follower")

#     for relation in active_followers:
#         follower = relation.follower

#         # Skip follower if remaining cash is below threshold
#         if relation.remaining_cash < MIN_CASH_THRESHOLD:
#             logger.info(
#                 f"Follower {follower.id} remaining_cash={relation.remaining_cash} below threshold, skipping new strategy {instance.strategy.name}"
#             )
#             continue

#         # Copy the new strategy to follower
#         copy_leader_strategies_to_follower(
#             leader_portfolio=leader_portfolio,
#             follower_portfolio=follower,
#             allocated_cash=relation.remaining_cash,
#             relation=relation,
#             buy_percent=Decimal("0.2"),
#             specific_strategy=instance.strategy
#         )

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




@receiver(post_save, sender=PortfolioStrategy)
def propagate_strategy_stop_to_followers(sender, instance, **kwargs):
    """
    When a leader stops a strategy, stop only copied versions for followers.
    """
    if instance.status != "STOPPED":
        return

    if instance.copy_relationship_id:
        return

    leader_portfolio = instance.portfolio
    followers = CopyRelationship.objects.filter(leader=leader_portfolio, is_active=True)

    for relation in followers:
        copied_ps_list = PortfolioStrategy.objects.filter(
            copy_relationship=relation,
            strategy=instance.strategy,
            status="ACTIVE"
        )
        for ps in copied_ps_list:
            from portfolios.services import unwind_copy_strategy_holdings
            returned_cash = unwind_copy_strategy_holdings(ps)
            ps.portfolio.cash_balance += returned_cash
            ps.portfolio.save(update_fields=["cash_balance"])
            ps.status = "STOPPED"
            ps.save(update_fields=["status"])



# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from strategies.models import PortfolioStrategy
# from .models import CopyRelationship
# from .services import copy_leader_strategies_to_follower, check_follower_strategy_health
# from portfolios.services import unwind_copy_strategy_holdings


# @receiver(post_save, sender=PortfolioStrategy)
# def auto_copy_new_strategy(sender, instance, created, **kwargs):
#     """
#     When a leader creates a new strategy allocation,
#     copy it to all active followers proportionally.
#     """

#     if not created:
#         return

#     # 🚫 Skip copied strategies
#     if instance.copy_relationship_id is not None:
#         return

#     leader_portfolio = instance.portfolio

#     active_followers = CopyRelationship.objects.filter(
#         leader=leader_portfolio,
#         is_active=True
#     ).select_related("follower")

#     leader_strategies = leader_portfolio.strategy_allocations.filter(status="ACTIVE")

#     leader_total_cash = sum(
#         ps.allocated_cash for ps in leader_strategies
#     )

#     if leader_total_cash <= 0:
#         return

#     for relation in active_followers:
#         follower = relation.follower
#         check_follower_strategy_health(follower)

#         # Strategy weight
#         weight = instance.allocated_cash / leader_total_cash
#         follower_cash = weight * relation.allocated_cash

#         if follower_cash <= 0:
#             continue

#         copy_leader_strategies_to_follower(
#             leader_portfolio=leader_portfolio,
#             follower_portfolio=follower,
#             allocated_cash=follower_cash,
#             relation=relation,
#             specific_strategy=instance.strategy
#         )


# @receiver(post_save, sender=PortfolioStrategy)
# def propagate_strategy_stop_to_followers(sender, instance, **kwargs):
#     """
#     When a leader stops a strategy, stop only copied versions for followers.
#     """

#     if instance.status != "STOPPED":
#         return

#     leader_portfolio = instance.portfolio

#     # Ignore follower-owned strategies
#     if instance.copy_relationship_id:
#         return

#     followers = CopyRelationship.objects.filter(
#         leader=leader_portfolio,
#         is_active=True
#     )

#     for relation in followers:
#         copied_ps = PortfolioStrategy.objects.filter(
#             copy_relationship=relation,
#             strategy=instance.strategy,
#             status="ACTIVE"
#         )

#         for ps in copied_ps:
#             returned_cash = unwind_copy_strategy_holdings(ps)

#             ps.portfolio.cash_balance += returned_cash
#             ps.portfolio.save(update_fields=["cash_balance"])

#             ps.status = "STOPPED"
#             ps.save(update_fields=["status"])


