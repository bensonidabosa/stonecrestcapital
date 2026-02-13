from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum

from .models import Portfolio
from .forms import KYCForm
from account.models import KYC
from plan.models import Plan
from transaction.forms import CustomerTransactionForm

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
    portfolio = get_object_or_404(Portfolio, user=request.user)

    context = {
        "current_url": request.resolver_match.url_name,
        'portfolio': portfolio,
    }
    return render(request, "customer/settings_security.html", context)


@login_required
def verify_kyc_view(request):
    portfolio = get_object_or_404(Portfolio, user=request.user)

    # Get or create KYC record
    kyc, created = KYC.objects.get_or_create(portfolio=portfolio)

    # If already verified, block resubmission
    if kyc.is_verified:
        messages.info(request, "Your identity has already been verified.")
        return redirect('customer:customer_dashboard')

    if request.method == "POST":
        form = KYCForm(request.POST, request.FILES, instance=kyc)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your KYC documents have been submitted successfully and are pending verification."
            )
            return redirect('customer:verify_kyc')
    else:
        form = KYCForm(instance=kyc)

    return render(
        request,
        'customer/verify_kyc.html',
        {
            'form': form,
            'kyc': kyc,
            'portfolio': portfolio,
            'current_url': request.resolver_match.url_name,
        }
    )



# transaction part
@login_required
@transaction.atomic
def customer_deposit_view(request):
    portfolio = request.user.portfolio
    deposit_transactions = portfolio.transactions.filter(
        transaction_type='DEPOSIT'
    )

    if request.method == "POST":
        form = CustomerTransactionForm(request.POST, transaction_type="DEPOSIT")

        if form.is_valid():
            trans = form.save(commit=False)
            trans.transaction_type = 'DEPOSIT'
            trans.portfolio = portfolio

            trans.balance = portfolio.cash_balance
            trans.save()

            messages.success(request, "Your deposit request has been received and is currently being processed.")
            return redirect('customer:customer_deposit')
        else:
            # 🔥 THIS shows you exactly why the form is invalid
            messages.error(request, "An error occurred while processing your request. Please try again or contact support if the issue persists.")
            print("FORM ERRORS:", form.errors)
            print("NON FIELD ERRORS:", form.non_field_errors())
    else:
        form = CustomerTransactionForm()

    return render(
        request,
        "customer/transactions/customer_deposit.html",
        {
            "form": form,
            "transactions": deposit_transactions
        }
    )


@login_required
@transaction.atomic
def customer_withdraw_view(request):
    portfolio = request.user.portfolio

    # Only fetch withdraw transactions once
    withdraw_transactions = portfolio.transactions.filter(
        transaction_type='WITHDRAW'
    )

    # Pending withdraws and total in a single query
    pending_withdraw_sum = withdraw_transactions.filter(
        status='PENDING'
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    if request.method == "POST":
        form = CustomerTransactionForm(request.POST, transaction_type="WITHDRAW")

        if form.is_valid():
            trans = form.save(commit=False)
            trans.transaction_type = 'WITHDRAW'
            trans.portfolio = portfolio

            # Check if balance is sufficient
            if portfolio.cash_balance < trans.amount:
                messages.error(
                    request,
                    "You don't have enough cash balance to complete this withdrawal."
                )
            else:

                if not portfolio.is_kyc_verified:
                    messages.error(
                        request,
                        "You must complete identity verification (KYC) before making a withdrawal."
                    )
                    return redirect('customer:verify_kyc')
                # Deduct from balance and save
                portfolio.cash_balance -= trans.amount
                portfolio.save()

                trans.balance = portfolio.cash_balance
                trans.save()
                messages.success(
                    request,
                    "Your withdrawal request has been submitted successfully and is pending processing."
                )
                return redirect('customer:customer_withdraw')

    else:
        form = CustomerTransactionForm()

    return render(
        request,
        "customer/transactions/customer_withdraw.html",
        {
            "form": form,
            "transactions": withdraw_transactions,
            "portfolio": portfolio,
            "pending_withdraw_sum": pending_withdraw_sum,
        }
    )