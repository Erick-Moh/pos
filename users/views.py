"""
users/views.py — Authentication and user management.
Single-instance: no tenant_slug, no tenancy filtering.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import IntegrityError

from django.conf import settings as django_settings
from users.decorators import login_required, admin_required
from .forms import StaffPinLoginForm, AdminPasswordLoginForm, UserCreateForm, UserEditForm
from .change_credentials_form import ChangeCredentialsForm
from .tasks import send_welcome_email
from .turnstile import verify_turnstile

User = get_user_model()


# ── Staff PIN login ────────────────────────────────────────────────────────────

def login_staff(request):
    """PIN-based login for cashiers and waiters."""
    if request.user.is_authenticated:
        return redirect('pos:dashboard')

    form = StaffPinLoginForm()
    if request.method == 'POST':
        token = request.POST.get('cf-turnstile-response', '')
        if not verify_turnstile(token, request.META.get('REMOTE_ADDR', '')):
            messages.error(request, 'Security check failed. Please try again.')
            return render(request, 'users/login_staff.html', {'form': form})

        form = StaffPinLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip().upper()
            user = authenticate(request, pin=form.cleaned_data['pin'], username=username)
            if user and user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}.')
                return redirect('pos:dashboard')
            messages.error(request, 'Invalid username or PIN.')

    return render(request, 'users/login_staff.html', {
        'form': form,
        'turnstile_site_key': django_settings.TURNSTILE_SITE_KEY,
    })


# ── Admin password login ───────────────────────────────────────────────────────

def login_admin(request):
    """Password-based login for administrators and managers."""
    if request.user.is_authenticated:
        return redirect('pos:dashboard')

    form = AdminPasswordLoginForm()
    if request.method == 'POST':
        token = request.POST.get('cf-turnstile-response', '')
        if not verify_turnstile(token, request.META.get('REMOTE_ADDR', '')):
            messages.error(request, 'Security check failed. Please try again.')
            return render(request, 'users/login_admin.html', {
                'form': form,
                'turnstile_site_key': django_settings.TURNSTILE_SITE_KEY,
            })

        form = AdminPasswordLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if not user:
                try:
                    candidate = User.objects.get(username=username, is_active=True)
                    if candidate.check_password(password) and candidate.is_admin_role:
                        candidate.backend = 'django.contrib.auth.backends.ModelBackend'
                        user = candidate
                except User.DoesNotExist:
                    pass

            if user and user.is_active and user.is_admin_role:
                login(request, user)
                messages.success(request, f'Welcome, {user.get_full_name() or user.username}.')
                return redirect('pos:dashboard')
            messages.error(request, 'Invalid credentials or insufficient privileges.')

    return render(request, 'users/login_admin.html', {
        'form': form,
        'turnstile_site_key': django_settings.TURNSTILE_SITE_KEY,
    })


# ── Logout ─────────────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('login')


# ── Profile & credential change ────────────────────────────────────────────────

@login_required
def profile_view(request):
    return render(request, 'users/profile.html', {'profile_user': request.user})


@login_required
def change_credentials(request):
    user = request.user
    if request.method == 'POST':
        form = ChangeCredentialsForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Credentials updated. You are now signed in.')
            return redirect('pos:dashboard')
    else:
        form = ChangeCredentialsForm(user=user)
    return render(request, 'users/change_credentials.html', {'form': form})


# ── User management (admin only) ───────────────────────────────────────────────

@login_required
@admin_required
def user_list(request):
    users = User.objects.exclude(
        is_staff=True, is_superuser=True
    ).order_by('role', 'username')
    return render(request, 'users/user_list.html', {'users': users})


@login_required
@admin_required
def user_create(request):
    default_password = settings.DEFAULT_USER_PASSWORD
    default_pin = settings.DEFAULT_USER_PIN
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            role = form.cleaned_data['role']
            user = form.save(commit=False)
            raw_username = form.cleaned_data['username'].strip().upper()
            if role in ['cashier', 'waiter']:
                user.set_pin(default_pin)
                user.set_unusable_password()
            else:
                user.set_password(default_password)
            user.username = raw_username
            try:
                user.save()
            except IntegrityError:
                messages.error(request, f'Username "{raw_username}" is already taken. Please choose a different username.')
                return render(request, 'users/user_form.html', {'form': form, 'action': 'Create'})
            if user.email:
                send_welcome_email.delay(
                    user_id=user.id,
                    username=raw_username,
                    credential_type='pin' if role in ['cashier', 'waiter'] else 'password',
                    credential_value=default_pin if role in ['cashier', 'waiter'] else default_password,
                    business_name=getattr(settings, 'BUSINESS_NAME', 'GetCore POS'),
                )
            messages.success(request, f'User "{raw_username}" created.')
            return redirect('users:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Create'})


@login_required
@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            if form.has_changed():
                if 'username' in form.changed_data:
                    user_obj.username = form.cleaned_data['username'].strip().upper()
                try:
                    form.save()
                except IntegrityError:
                    messages.error(request, f'Username "{user_obj.username}" is already taken.')
                    return render(request, 'users/user_form.html', {'form': form, 'action': 'Edit', 'obj': user_obj})
                messages.success(request, f'User "{user_obj.username}" updated.')
            return redirect('users:user_list')
    else:
        form = UserEditForm(instance=user_obj, initial={'username': user_obj.username})
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Edit', 'obj': user_obj})


@login_required
@admin_required
def user_toggle_active(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
    else:
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        status = 'activated' if user_obj.is_active else 'deactivated'
        messages.success(request, f'User "{user_obj.username}" {status}.')
    return redirect('users:user_list')
