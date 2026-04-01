"""
tenants/mixins.py
Utility mixin and helper for tenant-scoped views.

Usage in any view:
    from tenants.mixins import TenantQuerysetMixin

    def my_view(request):
        products = Product.objects.filter(tenant=request.tenant)
        ...
"""

from django.http import Http404
from django.shortcuts import redirect
from functools import wraps


def tenant_required(view_func):
    """
    Decorator: ensures request.tenant is set before entering the view.
    If not set (e.g. someone hits /some-unknown-path/), returns 404.
    """
    @wraps(view_func)
    def wrapper(request, tenant_slug, *args, **kwargs):
        if not getattr(request, 'tenant', None):
            raise Http404('Tenant not found.')
        return view_func(request, tenant_slug, *args, **kwargs)
    return wrapper


def get_tenant_or_404(request):
    """Shortcut: raises Http404 if no tenant on request."""
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        raise Http404('No tenant context.')
    return tenant
