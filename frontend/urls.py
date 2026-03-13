from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about-us/', views.about_view, name='about'),
    path('contact-us/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    path('mandates/', views.mandates_view, name='mandates'),
]