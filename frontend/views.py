from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from account.tokens import email_verification_token
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

from .forms import UserRegistrationForm, BootstrapLoginForm
from notification.email_utils import send_html_email
from account.models import User

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            # user.is_active = False
            user.is_email_verified = False
            user.save()

            # Build verification URL
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_verification_token.make_token(user)
            protocol = 'https' if not settings.DEBUG else 'http'
            verification_url = f"{protocol}://{current_site.domain}{reverse('frontend:verify_email', kwargs={'uidb64': uid, 'token': token})}"
            # verification_url = (
            #     f"http://{current_site.domain}"
            #     f"{reverse('frontend:verify_email', kwargs={'uidb64': uid, 'token': token})}"
            # )

            try:
                send_html_email(
                    subject="Verify your email address",
                    to_email=[user.email],
                    template_name="emails/verify_email.html",
                    context={
                        "user": user,
                        "verification_url": verification_url,
                    },
                )
            except Exception as e:
                # Email not configured yet — print link for manual testing
                print("\n" + "=" * 60)
                print("EMAIL NOT SENT (SMTP not configured)")
                print("Copy & paste this verification link in your browser:")
                print(verification_url)
                print("=" * 60 + "\n")

            # Pass user info via session to the account created page
            request.session['account_created_user'] = {
                'full_name': user.full_name,
                'email': user.email
            }
            return redirect('frontend:account_created')


        messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegistrationForm()

    return render(request, 'account/authentication/register.html', {'form': form})


def account_created_view(request):
    user_data = request.session.pop('account_created_user', None)
    if not user_data:
        # fallback if session expired or page accessed directly
        return redirect('account:login')

    context = {
        'full_name': user_data.get('full_name'),
        'email': user_data.get('email'),
    }
    return render(request, "account/authentication/account_created.html", context)


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and email_verification_token.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True
        user.save()

        login(request, user)
        messages.success(request, "Your email has been verified successfully!")
        return redirect('account:customer_dashboard')

    messages.error(request, "Verification link is invalid or expired.")
    return redirect('frontend:login')


class EmailLoginView(LoginView):
    template_name = 'account/authentication/login.html'
    authentication_form = BootstrapLoginForm

    def form_valid(self, form):
        user = form.get_user()

        # Block login if email not verified
        if not user.is_email_verified:
            # messages.warning(
            #     self.request,
            #     "Your email is not verified. Please check your inbox."
            # )

            # Provide a resend verification link
            self.request.session['resend_verification_user_id'] = user.id
            return redirect('frontend:resend_verification')

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Invalid email or password. Please check and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse_lazy('staff:admin_dashboard')

        return reverse_lazy('account:customer_dashboard')
    

def resend_verification_view(request):
    user_id = request.session.get('resend_verification_user_id')
    if not user_id:
        messages.error(request, "No user to verify.")
        return redirect('account:login')

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, "User not found.")
        return redirect('account:login')

    if request.method == 'POST':
        # Build verification URL
        current_site = get_current_site(request)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        protocol = 'https' if not settings.DEBUG else 'http'
        verification_url = f"{protocol}://{current_site.domain}{reverse('frontend:verify_email', kwargs={'uidb64': uid, 'token': token})}"

        try:
            send_html_email(
                subject="Verify your email address",
                to_email=[user.email],
                template_name="emails/verify_email.html",
                context={"user": user, "verification_url": verification_url},
            )
            messages.success(request, "Verification email sent. Check your inbox.")
        except Exception:
            # Dev mode: print link
            print("\nRESEND VERIFICATION LINK:")
            print(verification_url)
            messages.info(request, "Email not sent (SMTP not configured). Check console for link.")

        return redirect('frontend:login')

    # GET request: show page with button
    token_age = timezone.now() - user.date_joined
    token_expired = token_age > timedelta(hours=24)

    context = {
        "user": user,
        "token_expired": token_expired,
    }
    return render(request, "account/authentication/resend_verification.html", context)


class UserLogoutView(LogoutView):
    next_page = 'frontend:login' 


def home_view(request):
    return render(request, 'frontend/index.html')

def contact_view(request):
    return render(request, 'frontend/contact.html')
