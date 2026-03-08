from django.urls import path
from . import views

app_name = 'copytrade'

urlpatterns = [
    path('start/<portfolio_id>/', views.start_copy_view, name='start_copy'),
]