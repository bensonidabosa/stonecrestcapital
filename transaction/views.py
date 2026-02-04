from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from .forms import TransactionForm, CustomerTransactionForm
from staff.decorators import admin_staff_only

@login_required
@admin_staff_only
@transaction.atomic
def deposit_view(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            trans = form.save(commit=False)
            trans.transaction_type = 'DEPOSIT'
            trans.save()

            # Update the selected portfolio cash_balance
            portfolio = trans.portfolio
            portfolio.cash_balance += trans.amount
            portfolio.save()

            trans.balance = portfolio.cash_balance
            trans.save()

            messages.success(request, "Deposit successful!")
            return redirect('transaction:deposit')  # change to your url name

    else:
        form = TransactionForm()

    return render(request, "transactions/sdeposit.html", {"form": form})


@login_required
@admin_staff_only
@transaction.atomic
def withdraw_view(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            trans = form.save(commit=False)
            trans.transaction_type = 'WITHDRAW'

            portfolio = trans.portfolio

            # Check if balance is sufficient
            if portfolio.cash_balance < trans.amount:
                messages.error(request, "Insufficient cash balance for this withdrawal.")
                return render(request, "transactions/withdraw.html", {"form": form})

            # Deduct from balance and save
            portfolio.cash_balance -= trans.amount
            portfolio.save()

            trans.balance = portfolio.cash_balance
            trans.save()
            messages.success(request, "Withdrawal successful!")
            return redirect('transaction:withdraw')

    else:
        form = TransactionForm(initial={'transaction_type': 'Withdraw'})

    return render(request, "transactions/withdraw.html", {"form": form})


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
            return redirect('transaction:customer_deposit')
        else:
            # 🔥 THIS shows you exactly why the form is invalid
            messages.error(request, "An error occurred while processing your request. Please try again or contact support if the issue persists.")
            print("FORM ERRORS:", form.errors)
            print("NON FIELD ERRORS:", form.non_field_errors())
    else:
        form = CustomerTransactionForm()

    return render(
        request,
        "transactions/customer_deposit.html",
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
                    return redirect('portfolio:verify_kyc')
                # Deduct from balance and save
                portfolio.cash_balance -= trans.amount
                portfolio.save()

                trans.balance = portfolio.cash_balance
                trans.save()
                messages.success(
                    request,
                    "Your withdrawal request has been submitted successfully and is pending processing."
                )
                return redirect('transaction:customer_withdraw')

    else:
        form = CustomerTransactionForm()

    return render(
        request,
        "transactions/customer_withdraw.html",
        {
            "form": form,
            "transactions": withdraw_transactions,
            "portfolio": portfolio,
            "pending_withdraw_sum": pending_withdraw_sum,
        }
    )
