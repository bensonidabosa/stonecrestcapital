from django.urls import path

from . import views

app_name = 'staff'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),

    path('customers/', views.admin_customer_list_view, name='admin_customer_list'),
    path('customers/<int:user_id>/',views.admin_customer_detail_view,
    name='admin_customer_detail'),
    path("customers/<int:user_id>/edit/", views.admin_edit_customer_view,
    name="admin_edit_customer"),
    path("customers/<int:user_id>/delete/", views.admin_delete_customer_view,
    name="admin_delete_customer"),
    
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

    path('kyc-list/', views.admin_kyc_list_view,name='admin_kyc_list'),
    path('kyc/<int:kyc_id>/review/', views.admin_kyc_review_view,
    name='admin_kyc_review'),


]