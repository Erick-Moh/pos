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

User = get_user_model()


def login_view(request, tenant_slug):
    if request.user.is_authenticated:
        return redirect('tenant:pos:dashboard', tenant_slug=tenant_slug)

    staff_form = StaffPinLoginForm()
    admin_form = AdminPasswordLoginForm()
    active_tab = 'staff'

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'staff')

        if login_type == 'staff':
            active_tab = 'staff'
            staff_form = StaffPinLoginForm(request.POST)
            if staff_form.is_valid():
                user = authenticate(
                    request,
                    username=staff_form.cleaned_data['username'],
                )
                if user:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                    return redirect('tenant:pos:dashboard', tenant_slug=tenant_slug)
                messages.error(request, 'Invalid username or PIN.')

        elif login_type == 'admin':
            active_tab = 'admin'
            admin_form = AdminPasswordLoginForm(request.POST)
            if admin_form.is_valid():
                user = authenticate(
                    request,
                    username=admin_form.cleaned_data['username'],
                    password=admin_form.cleaned_data['password'],
                )
                if user and user.is_admin_role:
                    login(request, user)
                    messages.success(request, f'Welcome, {user.get_full_name() or user.username}!')
                    return redirect(request.GET.get('next') or 'tenant:pos:dashboard', tenant_slug=tenant_slug)
                messages.error(request, 'Invalid credentials or insufficient privileges.')

    return render(request, 'users/login.html', {
        'staff_form': staff_form,
        'admin_form': admin_form,
        'active_tab': active_tab,
        'tenant_slug': tenant_slug,
    })


def logout_view(request, tenant_slug):
    name = request.user.get_full_name() or request.user.username
    logout(request)
    messages.info(request, f'Goodbye, {name}. You have been logged out.')
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
            messages.success(request, 'Your credentials have been updated. Welcome!')
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
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.tenant = tenant
            user.save()
            messages.success(request, f'User "{user.username}" created successfully.')
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
            form.save()
            messages.success(request, f'User "{user_obj.username}" updated.')
            return redirect('tenant:users:user_list', tenant_slug=tenant_slug)
    else:
        form = UserEditForm(instance=user_obj)
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
