from django.shortcuts import get_object_or_404, redirect,render
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError

from customer.models import Portfolio
from .models import CopyRelationship
from .services import start_copy_service

def start_copy_view(request, portfolio_id):
    follower = request.user.portfolio
    leader = get_object_or_404(Portfolio, id=portfolio_id)

    if request.method == "POST":
        allocated_cash = Decimal(request.POST.get("allocated_cash", "0"))

        try:
            start_copy_service(
                follower=follower,
                leader=leader,
                allocated_cash=allocated_cash
            )

            messages.success(request, "Copy trading started successfully.")
            return redirect("customer:customer_dashboard")

        except (ValueError, ValidationError) as e:
            # e can be a list (ValidationError.messages) or string
            if hasattr(e, "messages"):
                msg = " ".join(str(m) for m in e.messages)
            else:
                msg = str(e)

            messages.error(request, msg)
            return redirect("copytrade:start_copy", portfolio_id=portfolio_id)

    context = {
        "leader": leader,
        "follower": follower
    }

    return render(request, "copytrade/start_copy.html", context)
