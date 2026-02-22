from .models import VIPRequest

def approve_vip_request(vip_request):
    if vip_request.status != VIPRequest.PENDING:
        return False  # can't approve non-pending request
    vip_request.status = VIPRequest.APPROVED
    vip_request.save(update_fields=['status'])
    
    user = vip_request.user
    user.is_vip = True
    user.save(update_fields=['is_vip'])
    return True


def reject_vip_request(vip_request, note=None):
    if vip_request.status != VIPRequest.PENDING:
        return False  # can't reject non-pending request
    vip_request.status = VIPRequest.REJECTED
    if note:
        vip_request.admin_note = note
    vip_request.save(update_fields=['status', 'admin_note'])
    return True
