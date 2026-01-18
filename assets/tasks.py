from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
# from .services import simulate_price_changes

# @csrf_exempt
# def update_prices_task(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'POST required'}, status=400)

#     simulate_price_changes()
#     return JsonResponse({'status': 'prices updated'})
