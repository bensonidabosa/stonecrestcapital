import time
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .decorators import admin_staff_only
from assets.forms import AssetForm
from assets.models import Asset
from trading.models import Trade
from strategies.models import Strategy
from strategies import forms 
from account.models import User
from account.forms import AdminCustomerEditForm


@login_required
@admin_staff_only
def admin_dashboard_view(request):
    all_assets = Asset.objects.all()

    context = {
        "current_url": request.resolver_match.url_name,
        'all_assets':all_assets
    }
    return render(request, 'account/admin/admin_dashboard.html', context )


@login_required
@admin_staff_only
def admin_customer_list_view(request):
    customers = User.objects.filter(is_staff=False)

    context = {
        "current_url": request.resolver_match.url_name,
        "customers": customers,
    }

    return render(request, 'account/admin/customer_list.html', context)


@login_required
@admin_staff_only
def admin_customer_detail_view(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False)

    context = {
        "current_url": request.resolver_match.url_name,
        "customer": customer,
    }

    return render(request, 'account/admin/customer_detail.html', context)


@login_required
@admin_staff_only
def admin_edit_customer_view(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False)

    if request.method == "POST":
        form = AdminCustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            alert_msg = f"{customer.full_name}'s information is updated successfuly."
            messages.success(request,  alert_msg)
            return redirect("staff:admin_customer_list")
    else:
        form = AdminCustomerEditForm(instance=customer)

    context = {
        "current_url": request.resolver_match.url_name,
        "customer": customer,
        "form": form,
    }

    return render(request, "account/admin/edit_customer.html", context)


@login_required
@admin_staff_only
def add_asset_view(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Asset is created successfully.")
            return redirect('staff:add_asset') 
    else:
        form = AssetForm()
    context = {
        "current_url": request.resolver_match.url_name,
        'form':form,
    }
    return render(request, 'account/admin/add_asset.html', context )


@login_required
@admin_staff_only
def edit_asset_view(request, asset_id):
    # Get the asset or 404
    asset = get_object_or_404(Asset, id=asset_id)

    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, "Asset updated successfully.")
            return redirect('staff:edit_asset', asset_id=asset.id)
    else:
        form = AssetForm(instance=asset)

    context = {
        "current_url": request.resolver_match.url_name,
        "form": form,
        "asset": asset,  # optional, in case template wants asset info
    }

    # Reuse the same template as add_asset
    return render(request, 'account/admin/add_asset.html', context)

@login_required
@admin_staff_only
def delete_asset_view(request, asset_id):
    if request.method == "POST":
        time.sleep(2)  # optional delay
        asset = get_object_or_404(Asset, id=asset_id)
        asset.delete()
        messages.success(request, "Asset deleted successfully.")
        return redirect('staff:admin_dashboard')
    

@login_required
@admin_staff_only
def admin_trade_list_view(request):
    trades = Trade.objects.select_related(
        'portfolio',
        'asset'
    ).order_by('-timestamp')

    context = {
        "current_url": request.resolver_match.url_name,
        "trades": trades,
    }
    return render(request, 'account/admin/trade_list.html', context)


@login_required
@admin_staff_only
def admin_strategy_list_view(request):
    strategies = Strategy.objects.prefetch_related(
        'allocations__asset'
    )

    context = {
        "current_url": request.resolver_match.url_name,
        "strategies": strategies,
    }
    return render(
        request,
        'account/admin/strategy_list.html',
        context
    )


@login_required
@admin_staff_only
def admin_strategy_create_view(request):
    if request.method == 'POST':
        form = forms.StrategyForm(request.POST)
        formset = forms.StrategyAllocationCreateFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            strategy = form.save()
            allocations = formset.save(commit=False)

            for allocation in allocations:
                allocation.strategy = strategy
                allocation.save()
            messages.success(request, "Strategy is Created successfully.")
            return redirect('staff:admin_strategy_list')
        else:
            messages.error(request, "Please fix the errors below.")
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
    else:
        form = forms.StrategyForm()
        formset = forms.StrategyAllocationCreateFormSet()

    context = {
        "current_url": request.resolver_match.url_name,
        "form": form,
        "formset": formset,
    }
    return render(
        request,
        'account/admin/strategy_form.html',
        context
    )

@login_required
@admin_staff_only
def admin_strategy_edit_view(request, pk):
    strategy = get_object_or_404(Strategy, pk=pk)

    if request.method == 'POST':
        time.sleep(3)
        form = forms.StrategyForm(request.POST, instance=strategy)
        formset = forms.StrategyAllocationEditFormSet(request.POST, instance=strategy)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Strategy updated successfully.")
            return redirect('staff:admin_strategy_list')
        else:
            messages.error(request, "Please fix the errors below.")
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
    else:
        form = forms.StrategyForm(instance=strategy)
        formset = forms.StrategyAllocationEditFormSet(instance=strategy)

    context = {
        "form": form,
        "formset": formset,
        "strategy": strategy,
        "current_url": request.resolver_match.url_name,
    }
    return render(request, 'account/admin/strategy_form.html', context)

@login_required
@admin_staff_only
def admin_strategy_delete_view(request, pk):
    strategy = get_object_or_404(Strategy, pk=pk)

    if request.method == 'POST':
        strategy.delete()
        messages.success(request, "Strategy is deleted successfully.")
        return redirect('staff:admin_strategy_list')

    context = {
        "current_url": request.resolver_match.url_name,
        "strategy": strategy,
    }
    return render(
        request,
        'account/admin/strategy_confirm_delete.html',
        context
    )
