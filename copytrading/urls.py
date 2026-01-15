from django.urls import path
from . import views

app_name = 'copytrading'
urlpatterns = [
    path('follow/<int:portfolio_id>/', views.follow_portfolio, name='follow_portfolio'),
    path('unfollow/<int:portfolio_id>/', views.unfollow_portfolio, name='unfollow_portfolio'),
    path('stop-copying/<int:leader_id>/', views.stop_copying_view,
    name='stop_copying'),
]
