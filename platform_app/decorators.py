"""
platform/decorators.py
Access control for the GetCore platform workspace.
Platform staff = Django is_staff or is_superuser flag.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def platform_login_required(view_func):
    """Redirect unauthenticated users to /platform/login/."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('platform:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Only Django staff/superusers may access platform views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('platform:login')
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'Platform access requires staff privileges.')
            return redirect('platform:login')
        return view_func(request, *args, **kwargs)
    return wrapper
