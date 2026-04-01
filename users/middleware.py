"""
users/middleware.py
Forces users to change their PIN/password on first login.
"""

from django.shortcuts import redirect


EXEMPT_SUBSTRINGS = [
    '/change-credentials/',
    '/logout/',
    '/login/',
    '/platform/',
    '/django-admin/',
    '/static/',
    '/media/',
]


class ForceCredentialChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path_info
            tenant = getattr(request, 'tenant', None)

            # Only enforce inside an active tenant scope
            if tenant and getattr(request.user, 'must_change_credentials', False):
                is_exempt = any(s in path for s in EXEMPT_SUBSTRINGS)
                if not is_exempt and not (request.user.is_staff and request.user.is_superuser):
                    # Build the URL directly — the 'users' namespace only
                    # exists under /<slug>/users/ so we cannot use reverse().
                    return redirect(f'/{tenant.slug}/users/change-credentials/')

        return self.get_response(request)
