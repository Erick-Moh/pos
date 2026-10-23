"""
users/middleware.py
Forces users to change their PIN/password on first login.
"""

from django.shortcuts import redirect


EXEMPT_SUBSTRINGS = [
    '/change-credentials/',
    '/logout',
    '/login',
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
            if getattr(request.user, 'must_change_credentials', False):
                path = request.path_info
                is_exempt = any(s in path for s in EXEMPT_SUBSTRINGS)
                if not is_exempt and not request.user.is_superuser:
                    return redirect('/users/change-credentials/')

        return self.get_response(request)
