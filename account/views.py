from django.shortcuts import render

def customer_dashboard_view(request):
    return render(request, 'account/customer/dashboard.html', {
        "current_url": request.resolver_match.url_name
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




