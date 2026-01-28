from django.urls import path
from . import views

app_name = 'frontend'
urlpatterns = [
    path('', views.home_view, name='home'),
    path('contact-us/', views.contact_view, name='contact'),

    path('register/', views.register_view, name='register'),
    path('account-created/', views.account_created_view, name='account_created'),
    path("verify-email/<uidb64>/<token>/", views.verify_email,
        name="verify_email",),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    path('login/', views.EmailLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
]
