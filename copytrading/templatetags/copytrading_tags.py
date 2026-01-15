from django import template
from copytrading.utils import is_copy_trading 

register = template.Library()

@register.filter
def portfolio_is_copy_trading(portfolio):
    return is_copy_trading(portfolio)
