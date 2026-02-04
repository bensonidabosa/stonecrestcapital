from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .services import rebalance_portfolio, pay_reit_dividends
from portfolios.models import Portfolio
from account.models import KYC
from account.forms import KYCForm


def rebalance_all_portfolios(request):
    portfolios = Portfolio.objects.filter(
        portfoliostrategy__isnull=False
    ).select_related('portfoliostrategy__strategy')

    for portfolio in portfolios:
        rebalance_portfolio(portfolio)

    return JsonResponse({"status": "ok"})


def run_dividends(request):
    pay_reit_dividends()
    return JsonResponse({"status": "dividends paid"})




@login_required
def verify_kyc_view(request):
    portfolio = get_object_or_404(Portfolio, user=request.user)

    # Get or create KYC record
    kyc, created = KYC.objects.get_or_create(portfolio=portfolio)

    # If already verified, block resubmission
    if kyc.is_verified:
        messages.info(request, "Your identity has already been verified.")
        return redirect('account:dashboard')  # change as needed

    if request.method == "POST":
        form = KYCForm(request.POST, request.FILES, instance=kyc)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your KYC documents have been submitted successfully and are pending verification."
            )
            return redirect('portfolio:verify_kyc')
    else:
        form = KYCForm(instance=kyc)

    return render(
        request,
        'account/customer/kyc/verify_kyc.html',
        {
            'form': form,
            'kyc': kyc,
            'portfolio': portfolio,
            'current_url': request.resolver_match.url_name,
        }
    )