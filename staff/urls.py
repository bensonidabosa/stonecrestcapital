from django.urls import path

from . import views

app_name = 'staff'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path("add/", views.add_asset_view, name="add_asset"),
    path('<int:asset_id>/edit/', views.edit_asset_view, name='edit_asset'),
    path('delete/<int:asset_id>/', views.delete_asset_view, name='delete_asset'),
    path('trades/', views.admin_trade_list_view, name='admin_trade_list'),
    path('strategies/', views.admin_strategy_list_view,name='admin_strategy_list'),
    path('strategies/create/', views.admin_strategy_create_view,name='admin_strategy_create'),
    path('strategies/<int:pk>/edit/', views.admin_strategy_edit_view,
    name='admin_strategy_edit'),
    path('strategies/<int:pk>/delete/', views.admin_strategy_delete_view,
    name='admin_strategy_delete'),

]