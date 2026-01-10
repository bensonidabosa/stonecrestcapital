from django.contrib import admin
from .models import Strategy, StrategyAllocation


class StrategyAllocationInline(admin.TabularInline):
    model = StrategyAllocation
    extra = 1


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'risk_level',
        'target_return_min',
        'target_return_max',
        'is_active',
    )
    list_filter = ('risk_level', 'is_active')
    search_fields = ('name',)

    inlines = [StrategyAllocationInline]
