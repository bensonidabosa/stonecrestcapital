from django.urls import path, include

from . import views

app_name = 'account'

urlpatterns = [
    path('dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path("portfolio/", views.portfolio_view, name="portfolio"),
    path('assets/', views.assets_view, name='assets'),
    path("assets-detail/", views.asset_detail, name="asset_detail"),
    path('stocks/', views.stocks_view, name='stocks'),
    path('stock-detail/', views.stock_detail_view, name='stock_detail'),
    path('reits/', views.reits_view, name='reits'),
    path('reits-detail/', views.reit_detail_view, name='reit_detail'),
    path('crypto/', views.crypto_view, name='crypto'),
    path('copy-trading/', views.copy_trading_view, name='copy_trading'),
    path('leader-profile/<leader_id>/', views.leader_profile_view, name='leader_profile'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('history/', views.trade_history_view, name='history'),
]