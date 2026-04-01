"""
users/decorators.py
Access control decorators for GetCore ERP.
All redirects are tenant-aware.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """Only admin/manager roles."""
    @wraps(view_func)
    def wrapper(request, tenant_slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('tenant:users:login', tenant_slug=tenant_slug)
        if request.user.is_admin_role:
            return view_func(request, tenant_slug, *args, **kwargs)
        messages.error(request, 'Access denied. This area requires administrator privileges.')
        return redirect('tenant:pos:dashboard', tenant_slug=tenant_slug)
    return wrapper


def pos_access_required(view_func):
    """Any authenticated user can access POS."""
    @wraps(view_func)
    def wrapper(request, tenant_slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login', tenant_slug=tenant_slug)
        return view_func(request, tenant_slug, *args, **kwargs)
    return wrapper


def login_required_tenant(view_func):
    """
    Tenant-aware login_required decorator.
    Redirects unauthenticated users to the tenant's login page.
    """
    @wraps(view_func)
    def wrapper(request, tenant_slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('tenant:users:login', tenant_slug=tenant_slug)
        return view_func(request, tenant_slug, *args, **kwargs)
    return wrapper
