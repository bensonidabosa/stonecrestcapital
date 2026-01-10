from django.urls import path, include

from . import views

app_name = 'strategy'

urlpatterns = [
    path('', views.strategy_list_view, name='strategy-list'),
    path('select/<int:strategy_id>/', views.select_strategy_view, name='select-strategy'),
]