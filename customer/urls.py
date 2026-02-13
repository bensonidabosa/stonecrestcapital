from django.urls import path

from . import views

app_name = 'account'

urlpatterns = [
    path('dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('copy-experts/', views.copy_experts, name='copy_experts'),
    path('settings-and-security/', views.settings_security, name='settings_security'),
]