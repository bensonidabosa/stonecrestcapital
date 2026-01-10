from django.urls import path, include

from . import views

app_name = 'account'

urlpatterns = [
    path('customer/dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('customer/stocks/', views.stocks_view, name='stocks'),
    path('customer/stock-detail/', views.stock_detail_view, name='stock_detail'),
    path('customer/reits/', views.reits_view, name='reits'),
    path('customer/reits-detail/', views.reit_detail_view, name='reit_detail'),
    path('customer/copy-trading/', views.copy_trading_view, name='copy_trading'),
    path('customer/wallet/', views.wallet_view, name='wallet'),
]