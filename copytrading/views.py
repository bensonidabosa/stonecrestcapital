from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from portfolios.models import Portfolio
from .models import CopyRelationship
from portfolios.services import liquidate_portfolio
from strategies.models import PortfolioStrategy


@login_required
def follow_portfolio(request, portfolio_id):
    follower = request.user.portfolio
    leader = get_object_or_404(Portfolio, id=portfolio_id)

    if follower == leader:
        return redirect('leaderboard')

    # 🚫 Lock copy trading if strategy is active
    if PortfolioStrategy.objects.filter(portfolio=follower).exists():
        messages.warning(
            request,
            "You must stop your active strategy before copy trading."
        )
        return redirect('account:copy_trading')

    CopyRelationship.objects.update_or_create(
        follower=follower,
        leader=leader,
        defaults={'is_active': True}
    )

    messages.success(request, "You are now copying this portfolio.")
    return redirect('account:copy_trading')


@login_required
def unfollow_portfolio(request, portfolio_id):
    follower = request.user.portfolio
    leader = get_object_or_404(Portfolio, id=portfolio_id)

    CopyRelationship.objects.filter(
        follower=follower,
        leader=leader
    ).update(is_active=False)

    return redirect('leaderboard')


@login_required
def stop_copying_view(request, leader_id):
    follower = request.user.portfolio

    relation = get_object_or_404(
        CopyRelationship,
        follower=follower,
        leader_id=leader_id,
        is_active=True
    )

    # Disable copying
    relation.is_active = False
    relation.save(update_fields=['is_active'])

    # Liquidate follower portfolio
    liquidate_portfolio(follower)
    messages.success(request, "You stopped copy trading and liquidated successfully.")
    return redirect('account:portfolio')
