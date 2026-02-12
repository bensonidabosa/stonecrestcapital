from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from .decorators import admin_staff_only
from account.models import User
from account.forms import AdminCustomerEditForm
from plan.models import Plan
from plan.forms import PlanForm


@login_required
@admin_staff_only
def admin_dashboard_view(request):
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')

    context = {
        "current_url": request.resolver_match.url_name,
        "customers": customers,
    }

    return render(request, 'staff/dashboard.html', context)


@login_required
@admin_staff_only
def admin_customer_detail_view(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False)

    context = {
        "current_url": request.resolver_match.url_name,
        "customer": customer,
    }

    return render(request, 'staff/customer_detail.html', context)


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
            return redirect("staff:admin_dashboard")
    else:
        form = AdminCustomerEditForm(instance=customer)

    context = {
        "current_url": request.resolver_match.url_name,
        "customer": customer,
        "form": form,
    }

    return render(request, "staff/edit_customer.html", context)


@login_required
@admin_staff_only
def admin_delete_customer_view(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False)

    if request.method == "POST":
        full_name = customer.full_name
        customer.delete()
        messages.success(
            request,
            f"{full_name} has been deleted successfully."
        )
        return redirect("staff:admin_dashboard")

    context = {
        "current_url": request.resolver_match.url_name,
        "customer": customer,
    }

    return render(request, "staff/delete_customer.html", context)


@login_required
@admin_staff_only
def admin_plan_list_view(request):
    plans = Plan.objects.all().order_by('-created_at')

    context = {
        "current_url": request.resolver_match.url_name,
        "plans": plans,
    }
    return render(
        request,
        'staff/plan_list.html',
        context
    )


@login_required
@admin_staff_only
def admin_plan_create_view(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)

        if form.is_valid():
            plan = form.save()
            messages.success(request, "Plan is Created successfully.")
            return redirect('staff:admin_plan_list')
        else:
            messages.error(request, "Please fix the errors below.")
            print("Form errors:", form.errors)
    else:
        form = PlanForm()

    context = {
        "current_url": request.resolver_match.url_name,
        "form": form,
    }
    return render(
        request,
        'staff/plan_form.html',
        context
    )


@login_required
@admin_staff_only
def admin_plan_edit_view(request, pk):
    plan = get_object_or_404(Plan, pk=pk)

    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan)

        if form.is_valid():
            form.save()
            messages.success(request, "Plan updated successfully.")
            return redirect('staff:admin_plan_list')
        else:
            messages.error(request, "Please fix the errors below.")
            print("Form errors:", form.errors)
    else:
        form = PlanForm(instance=plan)

    context = {
        "form": form,
        "plan": plan,
        "current_url": request.resolver_match.url_name,
    }
    return render(request, 'staff/plan_form.html', context)


@login_required
@admin_staff_only
def admin_plan_delete_view(request, pk):
    plan = get_object_or_404(Plan, pk=pk)

    if request.method == 'POST':
        plan.delete()
        messages.success(request, "plan is deleted successfully.")
        return redirect('staff:admin_plan_list')

    context = {
        "current_url": request.resolver_match.url_name,
        "plan": plan,
    }
    return render(
        request,
        'staff/plan_confirm_delete.html',
        context
    )