# tenants/middleware.py
"""
Resolves the current tenant from the URL slug and attaches it to the request.

URL pattern:  /<tenant_slug>/<app>/...
The middleware extracts <tenant_slug> from the path, looks up the Tenant,
and sets request.tenant.  If the slug is unknown or tenant is inactive,
a 404 is returned.

The root path (/) is exempt — it shows the public landing page.
"""

from django.http import Http404
from .models import Tenant

# URL prefixes that are NOT tenant-scoped
GLOBAL_PREFIXES = (
    '/django-admin/',
    '/static/',
    '/media/',
    '/__debug__/',
    '/platform/',
    '/service-worker.js'  # GetCore platform staff workspace — no tenant context
)

class TenantMiddleware:
    """
    Resolves request.tenant from the first path segment.

    Path:  /boutique-nairobi/pos/terminal/
    Slug:  boutique-nairobi
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Allow global prefixes and root through untouched
        if path == '/' or any(path.startswith(p) for p in GLOBAL_PREFIXES):
            request.tenant = None
            return self.get_response(request)

        # Extract the first segment: /segment/rest...
        parts = path.lstrip('/').split('/', 1)
        slug = parts[0]

        if not slug:
            request.tenant = None
            return self.get_response(request)

        # Resolve tenant
        try:
            tenant = Tenant.objects.get(slug=slug, is_active=True)
        except Tenant.DoesNotExist:
            raise Http404(f'No active tenant found for key: "{slug}"')

        request.tenant = tenant
        return self.get_response(request)
    