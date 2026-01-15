from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError
from django.contrib import messages

from portfolios.models import Portfolio
from .models import Strategy, PortfolioStrategy
from .services import execute_strategy, strategy_average_return, switch_strategy, liquidate_strategy

@login_required
def activate_strategy_view(request, strategy_id):
    portfolio = Portfolio.objects.get(user=request.user)
    strategy = get_object_or_404(Strategy, id=strategy_id)

    if hasattr(portfolio, 'portfoliostrategy'):
        # User already has a strategy → SWITCH
        try:
            switch_strategy(portfolio, strategy)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('strategies:list')
    else:
        # First time → APPLY
        PortfolioStrategy.objects.create(
            portfolio=portfolio,
            strategy=strategy
        )
        execute_strategy(portfolio, strategy)

    return redirect('account:portfolio')


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
def stop_strategy_view(request):
    portfolio = request.user.portfolio

    if not PortfolioStrategy.objects.filter(portfolio=portfolio).exists():
        messages.info(request, "No active strategy to stop.")
        return redirect('account:strategies')

    liquidate_strategy(portfolio)

    messages.success(
        request,
        "Strategy stopped. All assets sold and credited to cash balance."
    )
    return redirect('account:portfolio')

