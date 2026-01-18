# copytrading/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from strategies.models import PortfolioStrategy
from .models import CopyRelationship
from .services import copy_leader_strategies_to_follower, check_follower_strategy_health
from portfolios.services import unwind_copy_strategy_holdings


@receiver(post_save, sender=PortfolioStrategy)
def auto_copy_new_strategy(sender, instance, created, **kwargs):
    """
    When a leader creates a new strategy allocation,
    copy it to all active followers proportionally.
    """

    if not created:
        return

    # 🚫 Skip copied strategies
    if instance.copy_relationship_id is not None:
        return

    leader_portfolio = instance.portfolio

    active_followers = CopyRelationship.objects.filter(
        leader=leader_portfolio,
        is_active=True
    ).select_related("follower")

    leader_strategies = leader_portfolio.strategy_allocations.filter(status="ACTIVE")

    leader_total_cash = sum(
        ps.allocated_cash for ps in leader_strategies
    )

    if leader_total_cash <= 0:
        return

    for relation in active_followers:
        follower = relation.follower
        check_follower_strategy_health(follower)

        # Strategy weight
        weight = instance.allocated_cash / leader_total_cash
        follower_cash = weight * relation.allocated_cash

        if follower_cash <= 0:
            continue

        copy_leader_strategies_to_follower(
            leader_portfolio=leader_portfolio,
            follower_portfolio=follower,
            allocated_cash=follower_cash,
            relation=relation,
            specific_strategy=instance.strategy
        )


@receiver(post_save, sender=PortfolioStrategy)
def propagate_strategy_stop_to_followers(sender, instance, **kwargs):
    """
    When a leader stops a strategy, stop only copied versions for followers.
    """

    if instance.status != "STOPPED":
        return

    leader_portfolio = instance.portfolio

    # Ignore follower-owned strategies
    if instance.copy_relationship_id:
        return

    followers = CopyRelationship.objects.filter(
        leader=leader_portfolio,
        is_active=True
    )

    for relation in followers:
        copied_ps = PortfolioStrategy.objects.filter(
            copy_relationship=relation,
            strategy=instance.strategy,
            status="ACTIVE"
        )

        for ps in copied_ps:
            returned_cash = unwind_copy_strategy_holdings(ps)

            ps.portfolio.cash_balance += returned_cash
            ps.portfolio.save(update_fields=["cash_balance"])

            ps.status = "STOPPED"
            ps.save(update_fields=["status"])


# @receiver(post_save, sender=PortfolioStrategy)
# def auto_copy_new_strategy(sender, instance, created, **kwargs):
#     """
#     When a leader creates a new strategy allocation, copy it to all active followers.
#     """
#     if not created:
#         return  # Only react to new strategies

#     leader_portfolio = instance.portfolio

#     # Skip if this strategy belongs to a follower (avoid loops)
#     if CopyRelationship.objects.filter(follower=leader_portfolio).exists():
#         return

#     # Get active followers
#     active_followers = CopyRelationship.objects.filter(
#         leader=leader_portfolio,
#         is_active=True
#     ).select_related('follower')

#     total_leader_cash = instance.allocated_cash

#     for relation in active_followers:
#         follower_portfolio = relation.follower

#         check_follower_strategy_health(follower_portfolio)
#         follower_cash = (instance.allocated_cash / total_leader_cash) * relation.allocated_cash

#         # Copy the new strategy to follower
#         copy_leader_strategies_to_follower(
#             leader_portfolio=leader_portfolio,
#             follower_portfolio=follower_portfolio,
#             allocated_cash=follower_cash,
#             relation=relation,
#         )
