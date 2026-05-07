"""
users/views.py — Tenant-scoped authentication and user management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from users.decorators import login_required_tenant
from django.contrib import messages
from django.contrib.auth import get_user_model
from tenants.mixins import get_tenant_or_404
from .forms import StaffPinLoginForm, AdminPasswordLoginForm, UserCreateForm, UserEditForm
from .change_credentials_form import ChangeCredentialsForm
from .decorators import admin_required
from django.db.models import Q
from tenants.models import Tenant
from django.http import Http404
from django.conf import settings
from .tasks import send_welcome_email

User = get_user_model()


def login_view(request, tenant_slug):
    if request.user.is_authenticated:
        return redirect('tenant:pos:dashboard', tenant_slug=request.user.tenant.slug)

    staff_form = StaffPinLoginForm()
    admin_form = AdminPasswordLoginForm()
    active_tab = 'staff'

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'staff')

        if login_type == 'staff':
            staff_form = StaffPinLoginForm(request.POST)
            if staff_form.is_valid():
                user = authenticate(
                    request,
                    pin=staff_form.cleaned_data['pin'],
                    username=f'{tenant_slug}_{staff_form.cleaned_data["username"].strip().upper()}',
                )
                if user:
                    try:
                        tenant = get_object_or_404(Tenant, slug=user.tenant.slug, is_active=True)
                        if tenant.slug != tenant_slug:
                            messages.error(request, 'Invalid username or PIN.')
                            return render(request, 'users/login.html', {
                                'staff_form': staff_form,
                                'admin_form': admin_form,
                                'active_tab': active_tab,
                            })
                    except Http404:
                        messages.error(request, 'Invalid username or PIN.')
                        return render(request, 'users/login.html', {
                                'staff_form': staff_form,
                                'admin_form': admin_form,
                                'active_tab': active_tab,
                            })
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name or user.username}.')
                    return redirect('tenant:pos:dashboard', tenant_slug=tenant_slug)
                messages.error(request, 'Invalid username or PIN.')

        elif login_type == 'admin':
            active_tab = 'admin'
            admin_form = AdminPasswordLoginForm(request.POST)
            if admin_form.is_valid():
                user = authenticate(
                    request,
                    username=f'{tenant_slug}_{admin_form.cleaned_data["username"].strip().upper()}',
                    password=admin_form.cleaned_data['password'],
                )
                if user and user.is_admin_role:
                    try:
                        tenant = get_object_or_404(Tenant, slug=user.tenant.slug, is_active=True)
                        if tenant.slug != tenant_slug:
                            messages.error(request, 'Invalid credentials or insufficient privileges.')
                            return render(request, 'users/login.html', {
                                'staff_form': staff_form,
                                'admin_form': admin_form,
                                'active_tab': active_tab,
                            })
                    except Http404:
                        messages.error(request, 'Invalid username or password.')
                        return render(request, 'users/login.html', {
                                'staff_form': staff_form,
                                'admin_form': admin_form,
                                'active_tab': active_tab,
                            })
                    login(request, user)
                    messages.success(request, f'Welcome, {user.get_full_name() or user.username}.')
                    return redirect('tenant:pos:dashboard', tenant_slug=tenant_slug)
                messages.error(request, 'Invalid credentials or insufficient privileges.')

    return render(request, 'users/login.html', {
        'staff_form': staff_form,
        'admin_form': admin_form,
        'active_tab': active_tab,
    })


def logout_view(request, tenant_slug):
    name = request.user.get_full_name() or request.user.username
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('tenant:users:login', tenant_slug=tenant_slug)


@login_required_tenant
def profile_view(request, tenant_slug):
    return render(request, 'users/profile.html', {
        'profile_user': request.user,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
def change_credentials(request, tenant_slug):
    user = request.user
    if request.method == 'POST':
        form = ChangeCredentialsForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Credentials updated. You are now signed in.')
            return redirect('tenant:pos:dashboard', tenant_slug=tenant_slug)
    else:
        form = ChangeCredentialsForm(user=user)
    return render(request, 'users/change_credentials.html', {
        'form': form,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def user_list(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    users = User.objects.filter(Q(tenant=tenant) & ~(Q(is_staff=True) & Q(is_superuser=True))).order_by('role', 'username')
    return render(request, 'users/user_list.html', {
        'users': users,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def user_create(request, tenant_slug):
    tenant = get_tenant_or_404(request)
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
                user.is_staff = True
            user.tenant = tenant
            user.username = f'{tenant.slug}_{raw_username}'
            user.save()
            send_welcome_email.delay(
                user_id=user.id,
                username=raw_username,
                credential_type='pin' if role in ['cashier', 'waiter'] else 'password',
                credential_value=default_pin if role in ['cashier', 'waiter'] else default_password,
                tenant_name=tenant.name,
                tenant_slug=tenant.slug,
            )
            messages.success(request, f'User "{raw_username}" created.')
            return redirect('tenant:users:user_list', tenant_slug=tenant_slug)
    else:
        form = UserCreateForm()
    return render(request, 'users/user_form.html', {
        'form': form, 'action': 'Create', 'tenant_slug': tenant_slug,
    })

@login_required_tenant
@admin_required
def user_edit(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    user_obj = get_object_or_404(User, pk=pk, tenant=tenant)
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            if form.has_changed():
                if 'username' in form.changed_data:
                    raw_username = form.cleaned_data['username'].strip().upper()
                    user_obj.username = f'{tenant.slug}_{raw_username}'
                form.save()
                messages.success(request, f'User "{user_obj.username.strip(f"{tenant.slug}_")}" updated.')
            return redirect('tenant:users:user_list', tenant_slug=tenant_slug)
    else:
        initial_username = user_obj.username.strip(f'{tenant.slug}_')
        form = UserEditForm(instance=user_obj, initial={'username': initial_username})
    return render(request, 'users/user_form.html', {
        'form': form, 'action': 'Edit', 'obj': user_obj, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def user_toggle_active(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    user_obj = get_object_or_404(User, pk=pk, tenant=tenant)
    if user_obj == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
    else:
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        status = 'activated' if user_obj.is_active else 'deactivated'
        messages.success(request, f'User "{user_obj.username}" {status}.')
    return redirect('tenant:users:user_list', tenant_slug=tenant_slug)
