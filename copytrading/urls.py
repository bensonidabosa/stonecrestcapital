from django.urls import path
from . import views

app_name = 'copytrading'
urlpatterns = [
    path('follow/<int:portfolio_id>/', views.follow_portfolio, name='follow_portfolio'),
    path('stop-copying/<int:leader_id>/', views.stop_copying_view,
    name='stop_copying'),
    path('copy-trade-detail/<int:copy_id>/', views.user_copy_trade_detail,
    name='user_copy_trade_detail'),
]
