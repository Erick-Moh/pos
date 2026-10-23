"""
users/decorators.py
Access control decorators for GetCore.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def login_required(view_func):
    """Redirect unauthenticated users to the login page."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Only admin/manager roles may access this view."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_admin_role:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. This area requires administrator privileges.')
        return redirect('pos:dashboard')
    return wrapper


def admin_only(view_func):
    """Only the admin role may access this view (managers, cashiers, and waiters are excluded)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role == 'admin' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Only administrators can perform this action.')
        return redirect('pos:dashboard')
    return wrapper


def admin_or_cashier(view_func):
    """Admin and cashier roles may access this view (managers and waiters are excluded)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role in ('admin', 'cashier') or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Only administrators and cashiers can perform this action.')
        return redirect('pos:dashboard')
    return wrapper
