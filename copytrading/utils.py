from copytrading.models import CopyRelationship

def is_copy_trading(portfolio):
    return CopyRelationship.objects.filter(
        follower=portfolio,
        is_active=True
    ).exists()
