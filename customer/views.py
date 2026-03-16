from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from decimal import Decimal
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
import json
from django.db.models.functions import TruncDate
from datetime import datetime

from .models import Portfolio
from .forms import KYCForm
from account.models import KYC, VIPRequest
from account.forms import BootstrapPasswordChangeForm, VIPRequestForm
from plan.models import Plan, OrderPlan, OrderPlanItem
from transaction.forms import CustomerTransactionForm
from copytrade.models import CopyRelationship
from transaction.models import Coin, Wallet

@login_required
def customer_dashboard_view(request):
    portfolio = Portfolio.objects.get(user=request.user)
    plans = Plan.objects.filter(is_featured=True)

    # All active plans for this portfolio (mirrored or not)
    all_active_plans = OrderPlan.objects.filter(
        portfolio=portfolio,
        status=OrderPlan.STATUS_ACTIVE
    ).select_related("plan")

    active_plans = OrderPlan.objects.filter(
        portfolio=portfolio,
        status=OrderPlan.STATUS_ACTIVE,
        is_mirrowed = False
    ).select_related("plan")
    
    # Mirrored active plans (copied from leaders)
    mirrored_plans = OrderPlan.objects.filter(
        portfolio=portfolio,
        status=OrderPlan.STATUS_ACTIVE,
        is_mirrowed=True  # only mirrored plans
    ).select_related("plan")

    distribution = (
        all_active_plans
        .values("plan__plantype")
        .annotate(total=Sum("current_value"))
    )

    reit_total = Decimal("0.00")
    mandate_total = Decimal("0.00")

    for item in distribution:
        if item["plan__plantype"] == Plan.PlanType.REIT:
            reit_total = item["total"] or Decimal("0.00")
        elif item["plan__plantype"] == Plan.PlanType.MANDATE:
            mandate_total = item["total"] or Decimal("0.00")

    allocation_labels = ["REIT", "Asset Mandates"]
    allocation_values = [float(reit_total), float(mandate_total)]

    total_value = reit_total + mandate_total

    allocation_percentages = {
        "REIT": round((reit_total / total_value * 100), 2) if total_value > 0 else 0,
        "ASSET_MANDATES": round((mandate_total / total_value * 100), 2) if total_value > 0 else 0,
    }
    has_allocation = total_value > 0

    # Get all snapshots for those plans
    snapshots = (
        OrderPlanItem.objects
        .filter(order_plan__in=all_active_plans)
        .annotate(date=TruncDate("snapshot_at"))
        .values("date")
        .annotate(total_delta=Sum("delta_amount"))
        .order_by("date")
    )

    running_total = 0
    labels = []
    values = []

    for snap in snapshots:
        running_total += snap["total_delta"] or 0
        labels.append(snap["date"].strftime("%d %b"))
        values.append(float(running_total))
    has_performance = any(values)

    # --- Monthly PnL Calculation ---
    # Get current month
    now = datetime.now()
    
    monthly_snapshots = (
        OrderPlanItem.objects
        .filter(
            order_plan__in=active_plans,
            snapshot_at__year=now.year,
            snapshot_at__month=now.month
        )
        .aggregate(monthly_delta=Sum('delta_amount'))
    )

    monthly_delta = monthly_snapshots['monthly_delta'] or Decimal('0.00')

    # Total principal of active plans
    total_principal = active_plans.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')

    # Compute % increase this month
    if total_principal > 0:
        monthly_roi = (monthly_delta / total_principal) * Decimal('100')
    else:
        monthly_roi = Decimal('0.00')

    # mandate dognut
    mandate_value = active_plans.aggregate(total=Sum('current_value'))['total'] or 10
    cash_value = portfolio.cash_balance or 20

    donut_labels = ["Invested Mandates", "Cash Balance"]
    donut_values = [float(mandate_value), float(cash_value)]
    context = {
        "current_url": request.resolver_match.url_name,
        "portfolio": portfolio,
        "plans": plans,
        "active_plans": active_plans,
        "allocation_labels": json.dumps(allocation_labels),
        "allocation_values": json.dumps(allocation_values),
        "allocation_percentages": allocation_percentages,
        "has_allocation": has_allocation,
        "performance_labels": json.dumps(labels),
        "performance_values": json.dumps(values),
        "has_performance": has_performance,
        "monthly_delta": monthly_delta.quantize(Decimal('0.01')),
        "monthly_roi": monthly_roi.quantize(Decimal('0.1')),
        "donut_labels": json.dumps(donut_labels),
        "donut_values": json.dumps(donut_values),
        "mandate_value":mandate_value,
        "mirrored_plans":mirrored_plans,
    }

    return render(request, "customer/dashboard.html", context)


@login_required
def copy_experts(request):
    user = request.user
    user_portfolio = user.portfolio

    # Get all expert portfolios (excluding self and staff)
    portfolios = (
        Portfolio.objects
        .filter(user__can_be_copied=True)
        .exclude(user=user)
        .exclude(user__is_staff=True)
    )

    # Get all leaders the current user is already copying
    followed_relationships = CopyRelationship.objects.filter(
        follower=user_portfolio,
        is_active=True
    )
    followed_portfolios = set(rel.leader.id for rel in followed_relationships)

    # Check if user has a pending VIP request
    has_pending_vip_request = VIPRequest.objects.filter(user=user, status='pending').exists()

    context = {
        "current_url": request.resolver_match.url_name,
        "user": user,
        "portfolios": portfolios,
        "followed_portfolios": followed_portfolios,
        "has_pending_vip_request": has_pending_vip_request,
    }

    return render(request, "customer/copy_experts.html", context)


@login_required
def settings_security(request):
    portfolio = get_object_or_404(Portfolio, user=request.user)
    password_form = BootstrapPasswordChangeForm(portfolio.user)

    context = {
        "current_url": request.resolver_match.url_name,
        'portfolio': portfolio,
        "password_form":password_form,
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
    coins = Coin.objects.all()

    if request.method == "POST":
        form = CustomerTransactionForm(request.POST, transaction_type="DEPOSIT")

        if form.is_valid():
            trans = form.save(commit=False)
            trans.transaction_type = 'DEPOSIT'
            trans.portfolio = portfolio
            trans.balance = portfolio.cash_balance

            # ✅ Get the coin from POST (from your <select id="coin-select">)
            coin_id = request.POST.get("coin")  # this will work
            print(coin_id)
            if coin_id:
                try:
                    trans.coin = Coin.objects.get(id=coin_id)
                except Coin.DoesNotExist:
                    print('didnot work')
                    form.add_error(None, "Selected coin does not exist.")
                    return render(request, "your_template.html", {"form": form, "coins": coins})
            print('returned none')
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
            "transactions": deposit_transactions,
            "coins": coins
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


@login_required
def reits_view(request):
    portfolio = get_object_or_404(Portfolio, user=request.user)
    reit_plans = Plan.objects.filter(plantype="REIT")

    context = {
        "current_url": request.resolver_match.url_name,
        "portfolio": portfolio,
        "reit_plans": reit_plans,
    }
    return render(request, "customer/reits.html", context)


@login_required
def all_plans_view(request):
    portfolio = get_object_or_404(Portfolio, user=request.user)
    # plans = Plan.objects.all()
    plans = Plan.objects.exclude(plantype=Plan.PlanType.REIT)

    context = {
        "current_url": request.resolver_match.url_name,
        "portfolio": portfolio,
        "plans": plans,
    }
    return render(request, "customer/all_plan_test.html", context)


@login_required
def activate_plan_view(request, plan_id):
    portfolio = request.user.portfolio
    plan = get_object_or_404(Plan, id=plan_id)

    if request.method == "POST":
        allocated_cash = Decimal(request.POST.get("allocated_cash", "0"))

        if allocated_cash < plan.min_amount: 
            messages.error(request, f"Minimum amount for this plan is ${plan.min_amount}.") 
            return redirect('customer:activate_plan', plan_id=plan.pk)
        
        if allocated_cash > portfolio.cash_balance:
            messages.error(
                request,
                "Allocated cash exceeds your available cash balance."
            )
            return redirect('customer:activate_plan', plan_id=plan.pk)
        
        # 1️⃣ Deduct allocated cash from follower only once
        portfolio.cash_balance -= allocated_cash
        portfolio.save(update_fields=['cash_balance'])

        order = OrderPlan.objects.create( 
            portfolio=portfolio, 
            plan=plan, 
            principal_amount=allocated_cash, 
            current_value=allocated_cash, 
            start_at=timezone.now(), 
            status=OrderPlan.STATUS_ACTIVE, 
        )

        messages.success(request, f"'{plan.name}' activated with ${allocated_cash}.") 
        return redirect('customer:customer_dashboard')

    return render(
        request,
        "customer/activate_plan.html",
        {
            "plan": plan,
            "portfolio": portfolio
        }
    )


@login_required
def active_plan_list_view(request):
    portfolio = request.user.portfolio
    active_plans = OrderPlan.objects.filter(portfolio=portfolio)

    return render(
        request,
        "customer/active_plan_list.html",
        {
            "active_plans": active_plans,
            "portfolio": portfolio
        }
    )


@login_required
def orderplan_detail_view(request, order_id):
    portfolio = request.user.portfolio
    order = get_object_or_404(OrderPlan, pk=order_id, portfolio=portfolio) 
    
    snapshots_qs = order.items.order_by('snapshot_at')

    # -------- Pagination --------
    paginator = Paginator(snapshots_qs, 10)  # Show 10 snapshots per page
    page_number = request.GET.get('page')
    snapshots = paginator.get_page(page_number)

    # -------- Chart Data (Optional: Use ALL snapshots or only current page) --------
    # If you want chart to show ALL data:
    all_snapshots = snapshots_qs

    labels = [item.snapshot_at.strftime("%Y-%m-%d") for item in all_snapshots]
    values = [float(item.cumulative_amount or order.principal_amount) for item in all_snapshots]

    context = { 
        'order': order, 
        'snapshots': snapshots,   # paginated snapshots
        'labels': labels,
        'values': values,
    }

    return render(
        request,
        "customer/order_plan_detail.html",
        context
    )


@login_required
def change_password(request):
    if request.method != "POST":
        return redirect("customer:settings_security")

    form = BootstrapPasswordChangeForm(request.user, request.POST)

    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password updated successfully.")
    else:
        # Store form errors in messages
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{error}")

    return redirect("customer:settings_security")


@login_required
def submit_vip_request(request):
    user = request.user

    # Only handle POST submissions
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("customer:copy_experts")

    # Check if user is already VIP
    if user.is_vip:
        messages.warning(request, "You are already a VIP.")
        return redirect("customer:copy_experts")

    # Check if user has a pending request
    if VIPRequest.objects.filter(user=user, status=VIPRequest.PENDING).exists():
        messages.warning(request, "You already have a pending VIP request.")
        return redirect("customer:copy_experts")

    # Create the VIP request
    VIPRequest.objects.create(user=user)
    messages.success(request, "VIP request submitted successfully!")
    return redirect("customer:copy_experts")


@login_required
def wallet_view(request):
    portfolio = request.user.portfolio

    totals = OrderPlan.objects.filter(
        portfolio=portfolio
    ).aggregate(
        non_mirrored=Sum('principal_amount', filter=Q(is_mirrowed=False)),
        mirrored=Sum('principal_amount', filter=Q(is_mirrowed=True))
    )

    non_mirrored_total = totals['non_mirrored'] or 0
    mirrored_total = totals['mirrored'] or 0

    transactions = portfolio.transactions.all()

    return render(request, "customer/wallet.html", {
        "current_url": "wallet",
        "portfolio": portfolio,
        "non_mirrored_total": non_mirrored_total,
        "mirrored_total": mirrored_total,
        "transactions": transactions,
    })


# fetching crypto for deposit
from django.http import JsonResponse
def get_wallet(request):

    coin_id = request.GET.get("coin")

    wallet = Wallet.objects.filter(coin_id=coin_id).first()

    if wallet:
        data = {
            "wallet": wallet.wallet_address,
            "qr": wallet.qr_code.url if wallet.qr_code else ""
        }
    else:
        data = {}

    return JsonResponse(data)