from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Portfolio
from plan.models import Plan

@login_required
def customer_dashboard_view(request):
    portfolio = Portfolio.objects.get(user=request.user)
    plans = Plan.objects.filter(is_featured=True)

    context = {
        "current_url": request.resolver_match.url_name,
        "portfolio": portfolio,
        "plans": plans
    }
    return render(request, "customer/dashboard.html", context)


@login_required
def copy_experts(request):

    context = {
        "current_url": request.resolver_match.url_name,
    }
    return render(request, "customer/copy_experts.html", context)


@login_required
def settings_security(request):

    context = {
        "current_url": request.resolver_match.url_name,
    }
    return render(request, "customer/settings_security.html", context)
