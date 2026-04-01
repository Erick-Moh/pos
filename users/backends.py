"""
users/backends.py
Tenant-scoped authentication backends.
Users are scoped to a tenant — same username can exist across different tenants.
"""

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


def _get_tenant(request):
    return getattr(request, 'tenant', None)


class PinAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, pin=None, **kwargs):
        if not username or not pin:
            return None
        pin_str = str(pin).strip()
        if not pin_str.isdigit() or not (4 <= len(pin_str) <= 6):
            return None

        tenant = _get_tenant(request)
        qs = User.objects.filter(username=username, is_active=True)
        if tenant:
            qs = qs.filter(tenant=tenant)

        try:
            user = qs.get()
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

        if not user.is_floor_staff:
            return None
        if user.check_pin(pin_str):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class AdminAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        tenant = _get_tenant(request)
        qs = User.objects.filter(username=username, is_active=True)
        if tenant:
            qs = qs.filter(tenant=tenant)

        try:
            user = qs.get()
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

        if not user.is_admin_role:
            return None
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
