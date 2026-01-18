from django.urls import path

from . import views

app_name = 'assets'
urlpatterns = [
    path('manual-stimulation/', views.manual_stimulation, name="manual_stimulation"),
]