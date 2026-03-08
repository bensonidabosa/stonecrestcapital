from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import CopyRelationship, CopyTrade
from plan.models import OrderPlan

@transaction.atomic
def start_copy_service(*, follower, leader, allocated_cash):
    """
    Start copying a leader portfolio:
    - Deducts allocated cash from follower
    - Creates or updates the CopyRelationship
    - Mirrors existing active leader trades (20% of remaining_cash per trade)
    """

    if allocated_cash <= 0:
        raise ValidationError("Please allocate a positive cash amount.")

    if follower == leader:
        raise ValidationError("You cannot copy your own portfolio.")

    if allocated_cash > follower.cash_balance:
        raise ValidationError("Allocated cash exceeds your available balance.")

    # Deduct cash from follower
    follower.cash_balance -= allocated_cash
    follower.save(update_fields=["cash_balance"])

    # Create or update relationship
    relation, created = CopyRelationship.objects.update_or_create(
        follower=follower,
        leader=leader,
        defaults={
            "allocated_cash": allocated_cash,
            "is_active": True
        }
    )

    # Initialize remaining_cash only if newly created
    if created:
        relation.remaining_cash = allocated_cash
        relation.save(update_fields=["remaining_cash"])

        # Mirror existing active trades
        mirror_existing_trades(relation)

    return relation


def mirror_existing_trades(relationship):
    """
    Mirror leader's already active OrderPlans when a follower starts copying.
    Allocates trade_percentage (default 20%) of remaining cash per leader plan.
    """

    leader = relationship.leader
    follower = relationship.follower
    trade_percent = relationship.trade_percentage / Decimal("100")

    leader_plans = OrderPlan.objects.filter(
        portfolio=leader,
        status=OrderPlan.STATUS_ACTIVE,
        is_mirrowed=False
    )

    for leader_plan in leader_plans:

        if not relationship.can_copy_trade():
            break  # Stop if remaining cash is below minimum

        trade_amount = (relationship.remaining_cash * trade_percent).quantize(Decimal('0.01'))

        # Create follower order plan mirroring the leader plan
        follower_plan = OrderPlan.objects.create(
            portfolio=follower,
            plan=leader_plan.plan,
            principal_amount=trade_amount,
            current_value=trade_amount,
            is_mirrowed=True
        )

        # Create mapping in CopyTrade
        CopyTrade.objects.create(
            relationship=relationship,
            leader_orderplan=leader_plan,
            follower_orderplan=follower_plan,
            amount_used=trade_amount
        )

        # Reduce remaining cash
        relationship.remaining_cash -= trade_amount

    relationship.save(update_fields=["remaining_cash"])