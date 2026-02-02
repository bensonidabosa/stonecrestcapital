from django.urls import path
from . import views

app_name = 'transaction'
urlpatterns = [
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
]