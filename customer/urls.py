from django.urls import path

from . import views

app_name = 'account'

urlpatterns = [
    path('dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('copy-experts/', views.copy_experts, name='copy_experts'),
    path('settings-and-security/', views.settings_security, name='settings_security'),

    path('verify-kyc/', views.verify_kyc_view, name='verify_kyc'),
    path('reits/', views.reits_view, name='reits'),
    path('all-plans/', views.all_plans_view, name='all_plans'),

    # transaction
    path('user/deposit/', views.customer_deposit_view, name='customer_deposit'),
    path('user/withdraw/', views.customer_withdraw_view, name='customer_withdraw'),
]