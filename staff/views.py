from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required


from .decorators import admin_staff_only
from account.models import User
from account.forms import AdminCustomerEditForm


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