from django.urls import path, include

from . import views

app_name = 'strategy'

urlpatterns = [
    path('', views.strategy_list_view, name='strategy-list'),
    path('select/<int:strategy_id>/', views.activate_strategy_view, name='select-strategy'),
    path('leaderboard/', views.strategy_leaderboard, name='strategy_leaderboard'),
    path('stop-strategy/<strategy_allocation_id>/', views.stop_strategy_view, name='stop_strategy'),
]