from django.urls import path, include

from . import views

app_name = 'account'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('account-created/', views.account_created_view, name='account_created'),
    path("verify-email/<uidb64>/<token>/", views.verify_email,
        name="verify_email",),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    path('login/', views.EmailLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # forgot password
    path(
        "forgot-password/",
        views.forgot_password,
        name="forgot_password"
    ),

    path(
        "reset-password/<uidb64>/<token>/",
        views.reset_password,
        name="reset_password"
    ),

    # path(
    #     "reset-email-sent/",
    #     views.reset_email_sent,
    #     name="reset_email_sent"
    # ),
]