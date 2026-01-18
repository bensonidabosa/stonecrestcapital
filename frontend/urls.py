from django.urls import path
from . import views

app_name = 'frontend'
urlpatterns = [
    path('', views.home_view, name='home'),
    path('contact-us/', views.contact_view, name='contact'),
    path('register/', views.register_view, name='register'),
    path('login/', views.EmailLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
]
