from django.urls import path
from . import views

app_name = 'transaction'
urlpatterns = [
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdraw/', views.withdraw_view, name='withdraw'),

    # customer
    path('user/deposit/', views.customer_deposit_view, name='customer_deposit'),
    path('user/withdraw/', views.customer_withdraw_view, name='customer_withdraw'),
]