from decimal import Decimal
from trading.models import Trade
from .models import CopyRelationship


def mirror_trade(leader_portfolio, asset, trade_type, quantity):
    """
    Mirror a leader trade to all active followers
    """
    from trading.services import execute_buy, execute_sell

    # Do NOT mirror trades made by followers
    if CopyRelationship.objects.filter(follower=leader_portfolio, is_active=True).exists():
        print('stopped here')
        return

    print('passed one')

    followers = CopyRelationship.objects.filter(
        leader=leader_portfolio,
        is_active=True
    ).select_related('follower')

    leader_value = leader_portfolio.total_value()

    if leader_value <= 0:
        return

    for relation in followers:
        follower = relation.follower
        print('passed two')
        # Safety checks
        if follower.id == leader_portfolio.id:
            print('passed three')
            continue

        follower_value = follower.total_value()
        if follower_value <= 0:
            print('passed four')
            continue

        # Scale trade proportionally
        ratio = follower_value / leader_value
        follower_quantity = quantity * ratio

        if follower_quantity <= Decimal('0.0001'):
            print('passed 5')
            continue

        try:
            if trade_type == Trade.BUY:
                execute_buy(
                    portfolio=follower,
                    asset=asset,
                    quantity=follower_quantity
                )
            elif trade_type == Trade.SELL:
                execute_sell(
                    portfolio=follower,
                    asset=asset,
                    quantity=follower_quantity
                )
        except Exception:
            # Fail silently so leader trade is never blocked
            print('got here and failed here')
            continue
