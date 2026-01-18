from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from .services import stimulate_prices

@require_POST
def manual_stimulation(request):
    # Expect a hidden field in the form: <input type="hidden" name="direction" value="positive">
    direction = request.POST.get('direction', 'both').lower()
    if direction not in ['positive', 'negative', 'both']:
        direction = 'both'  # fallback just in case

    stimulate_prices(direction)
    messages.success(request, f"Asset prices were {direction}ly stimulated successfully.")
    return redirect('staff:admin_dashboard')


