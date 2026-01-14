from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from assets.models import Asset 
from portfolios.models import Portfolio
from portfolios.services import calculate_portfolio_value
from strategies.models import PortfolioStrategy


def customer_dashboard_view(request):
    portfolio = Portfolio.objects.get(user=request.user)

    holdings = portfolio.holdings.select_related('asset')
    snapshots = portfolio.snapshots.order_by('created_at')
    holding_count = holdings.count()

    # --------------------------------------------------
    # Asset Allocation (Market Value)
    # --------------------------------------------------
    allocation = {}
    for holding in holdings:
        asset_type = holding.asset.asset_type
        allocation.setdefault(asset_type, 0)
        allocation[asset_type] += holding.market_value()

    total_allocation_value = sum(allocation.values())

    allocation_percentages = {
        k: round((v / total_allocation_value) * 100, 2)
        if total_allocation_value > 0 else 0
        for k, v in allocation.items()
    }

    allocation_labels = list(allocation.keys())
    allocation_values = [float(v) for v in allocation.values()]

    ASSET_TYPE_LABELS = {
        "STOCK": "Stocks",
        "ETF": "ETFs",
        "REIT": "REITs",
    }

    # --------------------------------------------------
    # Recent Trades (last 7)
    # --------------------------------------------------
    TRADE_BADGES = {
        "BUY": "bg-primary",
        "SELL": "bg-danger",
        "DIVIDEND": "bg-warning text-dark",
        "REBALANCE": "bg-info text-dark",
        "SWITCH": "bg-secondary",
    }

    recent_trades = (
        portfolio.trades
        .select_related("asset")
        .all()[:7]
    )

    # --------------------------------------------------
    # Allocation Summary (Largest / Lowest)
    # --------------------------------------------------
    largest_allocation_label = lowest_allocation_label = None
    largest_allocation_percent = lowest_allocation_percent = 0

    if allocation_percentages:
        largest = max(allocation_percentages.items(), key=lambda x: x[1])
        lowest = min(allocation_percentages.items(), key=lambda x: x[1])

        largest_allocation_label = ASSET_TYPE_LABELS.get(largest[0])
        largest_allocation_percent = largest[1]

        lowest_allocation_label = ASSET_TYPE_LABELS.get(lowest[0])
        lowest_allocation_percent = lowest[1]

    # --------------------------------------------------
    # Best Performing Asset Type (ROI)
    # --------------------------------------------------
    asset_performance = {}

    for holding in holdings:
        asset_type = holding.asset.asset_type
        cost = holding.quantity * holding.average_price
        current_value = holding.market_value()

        if cost > 0:
            asset_performance.setdefault(asset_type, {"profit": 0, "cost": 0})
            asset_performance[asset_type]["profit"] += current_value - cost
            asset_performance[asset_type]["cost"] += cost

    best_asset_label = None
    best_asset_roi = 0

    if asset_performance:
        performance_roi = {
            k: (v["profit"] / v["cost"]) * 100
            for k, v in asset_performance.items()
            if v["cost"] > 0
        }

        if performance_roi:
            best = max(performance_roi.items(), key=lambda x: x[1])
            best_asset_label = ASSET_TYPE_LABELS.get(best[0])
            best_asset_roi = round(best[1], 2)

    # --------------------------------------------------
    # Risk Profile (from Strategy)
    # --------------------------------------------------
    risk_profile = "—"

    try:
        portfolio_strategy = (
            PortfolioStrategy.objects
            .select_related("strategy")
            .get(portfolio=portfolio)
        )

        risk_profile = portfolio_strategy.strategy.get_risk_level_display()

    except PortfolioStrategy.DoesNotExist:
        risk_profile = "—"

    # --------------------------------------------------
    # Diversification Score (0–10, Herfindahl Index)
    # --------------------------------------------------
    hhi = sum((p / 100) ** 2 for p in allocation_percentages.values())
    diversification_score = round((1 - hhi) * 10, 1)

    # --------------------------------------------------
    # Trades
    # --------------------------------------------------
    # trades = portfolio.trades.all()[:10]

    # --------------------------------------------------
    # Snapshots / Performance
    # --------------------------------------------------
    snapshot_labels = [s.created_at.strftime("%Y-%m-%d") for s in snapshots]
    snapshot_values = [float(s.total_value) for s in snapshots]

    if snapshots.count() >= 2:
        today_value = snapshots.last().total_value
        yesterday_value = snapshots.reverse()[1].total_value
        todays_pnl = today_value - yesterday_value
        todays_pnl_percent = (todays_pnl / yesterday_value) * 100
    else:
        todays_pnl = todays_pnl_percent = 0

    # --------------------------------------------------
    # ROI
    # --------------------------------------------------
    starting_cash = (
        snapshots.first().cash_balance
        if snapshots.exists()
        else portfolio.cash_balance
    )

    current_value = portfolio.total_value()
    roi_percent = (
        ((current_value - starting_cash) / starting_cash) * 100
        if starting_cash > 0 else 0
    )

    # --------------------------------------------------
    # Render
    # --------------------------------------------------
    return render(request, "account/customer/dashboard.html", {
        "current_url": request.resolver_match.url_name,
        "portfolio": portfolio,
        "holding_count": holding_count,

        # Allocation
        "allocation_labels": allocation_labels,
        "allocation_values": allocation_values,
        "allocation_percentages": allocation_percentages,

        # Allocation Summary
        "largest_allocation_label": largest_allocation_label,
        "largest_allocation_percent": largest_allocation_percent,
        "lowest_allocation_label": lowest_allocation_label,
        "lowest_allocation_percent": lowest_allocation_percent,

        # Best Performing
        "best_asset_label": best_asset_label,
        "best_asset_roi": best_asset_roi,

        # Risk & Diversification
        "risk_profile": risk_profile,
        "diversification_score": diversification_score,

        # Charts
        "snapshot_labels": snapshot_labels,
        "snapshot_values": snapshot_values,

        # Performance
        "todays_pnl": todays_pnl,
        "todays_pnl_percent": round(todays_pnl_percent, 2),
        "roi_percent": round(roi_percent, 2),

        # Trades
        # "trades": trades,
        "recent_trades": recent_trades,
        "trade_badges": TRADE_BADGES,

    })



@login_required
def portfolio_view(request):
    portfolio = Portfolio.objects.get(user=request.user)
    total_value = calculate_portfolio_value(portfolio)
    
    return render(request, "account/customer/portfolio.html", {
        "current_url": request.resolver_match.url_name,
        'portfolio': portfolio,
        'total_value': total_value,
    })

def assets_view(request):
    assets = Asset.objects.all().order_by('asset_type', 'symbol')
    return render(request, "account/customer/assets.html", {
        "current_url": request.resolver_match.url_name,
        'assets': assets
    })

def asset_detail(request, symbol):
    # asset = get_object_or_404(Asset, symbol=symbol)

    return render(request, "account/customer/asset_detail.html", {
        # "asset": asset,
        "current_url": "assets"
    })

def stocks_view(request):
    return render(request, "account/customer/stocks.html", {
        "current_url": request.resolver_match.url_name
    })

def stock_detail_view(request):
    return render(request, "account/customer/stock_detail.html", {
        "current_url": "stocks"
    })

    
def reits_view(request):
    return render(request, "account/customer/reits.html", {
        "current_url": request.resolver_match.url_name
    })

def reit_detail_view(request):
    return render(request, "account/customer/reit_detail.html", {
        "current_url": "reits"
    })

def copy_trading_view(request):
    return render(request, "account/customer/copy_trading.html", {
        "current_url": "copy_trading"
    })

def wallet_view(request):
    return render(request, "account/customer/wallet.html", {
        "current_url": "wallet"
    })


@login_required
def trade_history_view(request):
    portfolio = Portfolio.objects.get(user=request.user)
    trades = portfolio.trades.all()
    return render(request, 'account/customer/trade_history.html', {'trades': trades, "current_url": request.resolver_match.url_name,})




