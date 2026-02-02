from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from decimal import Decimal

from portfolios.models import Portfolio
from strategies.models import StrategyHolding
from .models import CopyRelationship
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

        # 1️⃣ Deduct allocated cash from follower only once
        follower.cash_balance -= allocated_cash
        follower.save(update_fields=['cash_balance'])

        # 2️⃣ Create or update copy relationship
        relation, created = CopyRelationship.objects.update_or_create(
            follower=follower,
            leader=leader,
            defaults={
                'allocated_cash': allocated_cash,
                'is_active': True
            }
        )

        if created:
            relation.remaining_cash = allocated_cash
            relation.save(update_fields=['remaining_cash'])


        # 3️⃣ Copy leader strategies to follower
        copy_leader_strategies_to_follower(
            leader_portfolio=leader,
            follower_portfolio=follower,
            # allocated_cash=allocated_cash,
            relation=relation,
            buy_percent=Decimal("0.2"), # 20% of remaining cash per leader strategy
            min_cash=Decimal("200")
        )

        messages.success(request, f"You are now copying {leader.user.nick_name}'s strategies.")
        return redirect('account:copy_trading')

    # GET → show allocation form
    return render(request, "account/customer/copy_trading/follow_form.html", {
        "leader": leader,
        "follower": follower
    })



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
def user_copy_trade_detail(request, copy_id):
    portfolio = request.user.portfolio

    # Get the active copy
    copy = get_object_or_404(
        CopyRelationship.objects.select_related('leader__user'),
        id=copy_id,
        follower=portfolio,
        is_active=True
    )

    # Get strategies attached to this copy
    copy_strategy_allocs = portfolio.strategy_allocations.filter(
        copy_relationship=copy,
        status='ACTIVE'
    ).select_related('strategy')

    # Build allocation map: asset_id -> allocated_cash
    asset_alloc_map = {}
    for sa in copy_strategy_allocs:
        for alloc in sa.strategy.allocations.select_related('asset'):
            allocated_cash = (alloc.percentage / Decimal('100.0')) * sa.allocated_cash
            asset_alloc_map[alloc.asset.id] = (
                asset_alloc_map.get(alloc.asset.id, Decimal('0.00')) + allocated_cash
            )

    # Filter holdings for this copy's assets and calculate differences
    holdings = []
    for holding in portfolio.holdings.select_related('asset'):
        if holding.asset.id in asset_alloc_map:
            holding.allocated_cash = asset_alloc_map[holding.asset.id]
            holding.difference = holding.market_value() - holding.allocated_cash

            # Compute decimals for display
            if holding.asset.asset_type == "CRYPTO":
                holding.decimals = 8
            else:
                holding.decimals = 2

            # Compute P/L and % for display
            holding.market_value_calc = holding.market_value()
            holding.unrealized_pnl_calc = holding.unrealized_pnl()
            holding.unrealized_pnl_percent_calc = holding.unrealized_pnl_percent()

            holdings.append(holding)

    # Split holdings by asset type
    stock_holdings = [h for h in holdings if h.asset.asset_type == "STOCK"]
    reit_holdings = [h for h in holdings if h.asset.asset_type == "REIT"]
    crypto_holdings = [h for h in holdings if h.asset.asset_type == "CRYPTO"]

    # --- Copy summary ---
    invested = copy.invested  # allocated - remaining
    current_value = sum(h.market_value() for h in holdings)
    percent_change = ((current_value - invested) / invested * 100) if invested else 0

    context = {
        'copy': copy,
        'copy_strategy_allocs': copy_strategy_allocs,
        'stock_holdings': stock_holdings,
        'reit_holdings': reit_holdings,
        'crypto_holdings': crypto_holdings,
        'invested': invested,
        'current_value': current_value,
        'percent_change': percent_change,
    }

    return render(request, 'account/customer/copy_trading/copy_trade_detail.html', context)




# @login_required
# def user_copy_trade_detail(request, copy_id):
#     portfolio = request.user.portfolio

#     # Get the active copy
#     copy = get_object_or_404(
#         CopyRelationship.objects.select_related('leader__user'),
#         id=copy_id,
#         follower=portfolio,
#         is_active=True
#     )

#     # Get strategies attached to this copy
#     copy_strategy_allocs = portfolio.strategy_allocations.filter(
#         copy_relationship=copy,
#         status='ACTIVE'
#     ).select_related('strategy')

#     # Build allocation map: asset_id -> allocated_cash
#     asset_alloc_map = {}
#     for sa in copy_strategy_allocs:
#         for alloc in sa.strategy.allocations.select_related('asset'):
#             allocated_cash = (alloc.percentage / 100) * sa.allocated_cash
#             asset_alloc_map[alloc.asset.id] = (
#                 asset_alloc_map.get(alloc.asset.id, Decimal("0.00")) + allocated_cash
#             )

#     # Filter holdings for this copy's assets and calculate differences
#     holdings = []
#     for holding in portfolio.holdings.select_related('asset'):
#         if holding.asset.id in asset_alloc_map:
#             holding.allocated_cash = asset_alloc_map[holding.asset.id]
#             holding.difference = holding.market_value() - holding.allocated_cash
#             holdings.append(holding)

#     # Split holdings by asset type
#     stock_holdings = [h for h in holdings if h.asset.asset_type == "STOCK"]
#     reit_holdings = [h for h in holdings if h.asset.asset_type == "REIT"]
#     crypto_holdings = [h for h in holdings if h.asset.asset_type == "CRYPTO"]

#     # --- New: calculate copy summary ---
#     invested = copy.invested  # allocated - remaining
#     current_value = sum(h.market_value() for h in holdings)  # total market value
#     percent_change = ((current_value - invested) / invested * 100) if invested else 0

#     return render(
#         request,
#         'account/customer/copy_trading/copy_trade_detail.html',
#         {
#             'copy': copy,
#             'copy_strategy_allocs': copy_strategy_allocs,
#             'stock_holdings': stock_holdings,
#             'reit_holdings': reit_holdings,
#             'crypto_holdings': crypto_holdings,
#             # --- summary context ---
#             'invested': invested,
#             'current_value': current_value,
#             'percent_change': percent_change,
#         }
#     )




