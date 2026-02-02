
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontend.urls', namespace='frontend')),
    path('account/', include('account.urls', namespace='account')),
    path('assets/', include('assets.urls', namespace='assets')),
    path('staff/', include('staff.urls', namespace='staff')),
    path('trading/', include('trading.urls', namespace='trading')),
    path('strategy/', include('strategies.urls', namespace='strategy')),
    path('portfolio/', include('portfolios.urls', namespace='portfolio')),
    path('copytrading/', include('copytrading.urls', namespace='copytrading')),
    path('otp/', include('otp.urls', namespace='otp')),
    path('transaction/', include('transaction.urls', namespace='transaction')),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)