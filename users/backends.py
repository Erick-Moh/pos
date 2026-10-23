"""
users/backends.py
Single-instance authentication backends — no tenant filtering.
"""

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class PinAuthBackend(BaseBackend):
    """Staff login: username + 4-digit PIN."""

    def authenticate(self, request, username=None, pin=None, **kwargs):
        if not username or not pin:
            return None
        pin_str = str(pin).strip()
        if not pin_str.isdigit() or not (4 <= len(pin_str) <= 6):
            return None

        try:
            user = User.objects.get(username=username, is_active=True)
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
    """Admin/manager login: username + password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = User.objects.get(username=username, is_active=True)
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
