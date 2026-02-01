from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError
from django.contrib import messages

from portfolios.models import Portfolio, PortfolioSnapshot
from .models import Strategy, PortfolioStrategy
from .services import execute_strategy, strategy_average_return, liquidate_strategy

@login_required
def activate_strategy_view(request, strategy_id):
    portfolio = request.user.portfolio
    strategy = get_object_or_404(Strategy, id=strategy_id)

    # Prevent duplicate activation of same strategy
    if PortfolioStrategy.objects.filter(
        portfolio=portfolio,
        strategy=strategy,
        status='ACTIVE'
    ).exists():
        messages.info(request, "This strategy is already active.")
        return redirect('account:portfolio')

    if request.method == "POST":
        allocated_cash = Decimal(request.POST.get("allocated_cash", "0"))

        if allocated_cash <= 0:
            messages.error(request, "Please allocate a positive cash amount.")
            return redirect('strategies:list')

        if allocated_cash > portfolio.cash_balance:
            messages.error(
                request,
                "Allocated cash exceeds your available cash balance."
            )
            return redirect('strategies:list')
        
        # 1️⃣ Deduct allocated cash from follower only once
        portfolio.cash_balance -= allocated_cash
        portfolio.save(update_fields=['cash_balance'])

        # Create strategy allocation
        ps = PortfolioStrategy.objects.create(
            portfolio=portfolio,
            strategy=strategy,
            allocated_cash=allocated_cash,
            remaining_cash=allocated_cash,
            status='ACTIVE'
        )

        # Execute strategy USING allocated cash only
        execute_strategy(
            portfolio=portfolio,
            # strategy=strategy,
            strategy_allocation=ps
        )

        messages.success(
            request,
            f"Strategy {strategy.name} activated with ${allocated_cash}."
        )
        return redirect('account:portfolio')

    return render(
        request,
        "account/customer/strategies/activate_strategy.html",
        {
            "strategy": strategy,
            "portfolio": portfolio
        }
    )



@login_required
def strategy_list_view(request):
    strategies = Strategy.objects.filter(is_active=True)

    try:
        portfolio = Portfolio.objects.get(user=request.user)
    except Portfolio.DoesNotExist:
        portfolio = None
    return render(request, 'account/customer/strategies/list.html', {
        'strategies': strategies,
        'portfolio': portfolio,
    })


@login_required
def strategy_leaderboard(request):
    strategies = Strategy.objects.filter(is_active=True)

    leaderboard = []
    for strategy in strategies:
        leaderboard.append({
            'strategy': strategy,
            'avg_return': strategy_average_return(strategy),
            'asset_types': ", ".join(strategy.asset_types()),
        })

    leaderboard.sort(
        key=lambda x: x['avg_return'],
        reverse=True
    )

    return render(
        request,
        'account/customer/strategies/leaderboard.html',
        {'leaderboard': leaderboard}
    )


@login_required
def stop_strategy_view(request, strategy_allocation_id):
    portfolio = request.user.portfolio

    ps = get_object_or_404(
        PortfolioStrategy,
        id=strategy_allocation_id,
        portfolio=portfolio
    )

    if ps.status != 'ACTIVE':
        messages.info(request, "This strategy is already stopped.")
        return redirect('account:portfolio')

    # Liquidate only this strategy
    liquidate_strategy(
        portfolio=portfolio,
        strategy_allocation=ps
    )

    messages.success(
        request,
        f"Strategy {ps.strategy.name} stopped and cash returned."
    )

    return redirect('account:portfolio')


def strategy_list_by_type(request, strategy_type):
    strategies = Strategy.objects.filter(strategy_type=strategy_type, is_active=True)
    return render(
        request,
        'account/customer/strategies/strategy_list.html',
        {
            'strategies': strategies,
            'strategy_type': strategy_type
        }
    )


