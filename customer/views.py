from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Portfolio

@login_required
def customer_dashboard_view(request):
    # portfolio = Portfolio.objects.get(user=request.user)

    context = {
        "current_url": request.resolver_match.url_name,
        # "portfolio": portfolio,
    }
    return render(request, "customer/dashboard.html", context)
