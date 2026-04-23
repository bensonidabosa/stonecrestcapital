from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import datetime
import traceback

from notification.email_utils import send_html_email

User = get_user_model()


@receiver(post_save, sender=User)
def notify_admin_new_user(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        send_html_email(
            subject="New user registration",
            to_email=[settings.ADMIN_EMAIL],
            # to_email=[admin[1] for admin in settings.ADMINS],  # ("Name", "email")
            template_name="notification/emails/admin_new_user.html",
            context={
                "user": instance,
                "site_name": settings.SITE_NAME,
                "year": datetime.now().year,
            },
        )

    except Exception:
        print("\nADMIN EMAIL ERROR:")
        traceback.print_exc()