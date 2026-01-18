from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from decimal import Decimal

from portfolios.models import Portfolio
from .models import CopyRelationship
from portfolios.services import liquidate_portfolio
from strategies.models import PortfolioStrategy
from .services import copy_leader_strategies_to_follower, stop_copying_and_unwind

@login_required
def follow_portfolio(request, portfolio_id):
    follower = request.user.portfolio
    leader = get_object_or_404(Portfolio, id=portfolio_id)

    if follower == leader:
        messages.warning(request, "You cannot copy your own portfolio.")
        return redirect('leaderboard')

    if request.method == "POST":
        allocated_cash = Decimal(request.POST.get("allocated_cash", "0"))

        if allocated_cash <= 0:
            messages.error(request, "Please allocate a positive cash amount.")
            return redirect('account:copy_trading')

        if allocated_cash > follower.cash_balance:
            messages.error(request, "Allocated cash exceeds your available cash balance.")
            return redirect('account:copy_trading')

        # Deduct allocated cash from follower
        follower.cash_balance -= allocated_cash
        follower.save(update_fields=['cash_balance'])

        # Create or update copy relationship
        relation, created = CopyRelationship.objects.update_or_create(
            follower=follower,
            leader=leader,
            defaults={'allocated_cash': allocated_cash, 'is_active': True}
        )

        # Copy all active leader strategies proportionally
        copy_leader_strategies_to_follower(leader, follower, allocated_cash, relation)

        messages.success(request, f"You are now copying {leader.user.nick_name}'s trades and strategies.")
        return redirect('account:copy_trading')

    # GET → show form to enter allocated cash
    return render(request, "account/customer/copy_trading/follow_form.html", {
        "leader": leader,
        "follower": follower
    })

# @login_required
# def follow_portfolio(request, portfolio_id):
#     follower = request.user.portfolio
#     leader = get_object_or_404(Portfolio, id=portfolio_id)

#     if follower == leader:
#         return redirect('leaderboard')

#     # 🚫 Lock copy trading if strategy is active
#     if PortfolioStrategy.objects.filter(portfolio=follower).exists():
#         messages.warning(
#             request,
#             "You must stop your active strategy before copy trading."
#         )
#         return redirect('account:copy_trading')

#     CopyRelationship.objects.update_or_create(
#         follower=follower,
#         leader=leader,
#         defaults={'is_active': True}
#     )

#     messages.success(request, "You are now copying this portfolio.")
#     return redirect('account:copy_trading')


# @login_required
# def stop_copying_view(request, leader_id):
#     follower = request.user.portfolio

#     relation = get_object_or_404(
#         CopyRelationship,
#         follower=follower,
#         leader_id=leader_id,
#         is_active=True
#     )

#     # Disable copying
#     relation.is_active = False
#     relation.save(update_fields=['is_active'])

#     # Liquidate follower portfolio
#     liquidate_portfolio(follower)
#     messages.success(request, "You stopped copy trading and liquidated successfully.")
#     return redirect('account:portfolio')


@login_required
def stop_copying_view(request, leader_id):
    follower = request.user.portfolio
    leader = get_object_or_404(Portfolio, id=leader_id)

    stop_copying_and_unwind(
        follower_portfolio=follower,
        leader_portfolio=leader
    )

    messages.success(
        request,
        "Copy trading stopped. All copied strategies have been liquidated."
    )
    return redirect("account:portfolio")



@login_required
def unfollow_portfolio(request, portfolio_id):
    follower = request.user.portfolio
    leader = get_object_or_404(Portfolio, id=portfolio_id)

    CopyRelationship.objects.filter(
        follower=follower,
        leader=leader
    ).update(is_active=False)

    return redirect('leaderboard')