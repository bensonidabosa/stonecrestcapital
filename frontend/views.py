from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .forms import UserRegistrationForm

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('account:customer_dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'account/authentication/register.html', {'form': form})

class EmailLoginView(LoginView):
    template_name = 'account/authentication/login.html'

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse_lazy('staff:admin_dashboard')

        return reverse_lazy('account:customer_dashboard')


class UserLogoutView(LogoutView):
    next_page = 'frontend:login' 


def home_view(request):
    return render(request, 'frontend/index.html')
