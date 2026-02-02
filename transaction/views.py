from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required

from .forms import TransactionForm
from staff.decorators import admin_staff_only

@login_required
@admin_staff_only
@transaction.atomic
def deposit_view(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            trans = form.save(commit=False)
            trans.transaction_type = 'Deposit'
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
            trans.transaction_type = 'Withdraw'

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

            trans.save()
            messages.success(request, "Withdrawal successful!")
            return redirect('transaction:withdraw')

    else:
        form = TransactionForm(initial={'transaction_type': 'Withdraw'})

    return render(request, "transactions/withdraw.html", {"form": form})
