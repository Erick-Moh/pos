"""
users/models.py
Custom User Model for GetCore ERP.

Supports two login modes:
  - Staff:  Username + 4-digit PIN (fast floor access)
  - Admin:  Username + Strong Password (back-office full access)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class GetCoreUser(AbstractUser):
    """
    Extended user model.
    All users share the same model; role is determined by `role` field.
    Admins use standard Django password; staff use hashed_pin.
    """


    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('cashier', 'Cashier / Staff'),
        ('waiter', 'Waiter / Floor Staff'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='cashier',
        help_text='Determines access level and login method.'
    )

    # 4-digit PIN stored as a Django-hashed value (bcrypt / PBKDF2)
    # Only set for staff/waiter roles. Admins/managers use standard password.
    hashed_pin = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text='Hashed 4-digit PIN for floor staff quick login.'
    )

    # Profile fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    is_active_shift = models.BooleanField(
        default=False,
        help_text='True when the staff member is currently on duty.'
    )
    must_change_credentials = models.BooleanField(
        default=True,
        help_text='Forces the user to change their PIN/password on next login.'
    )

    # Timestamps are inherited from AbstractUser (date_joined, last_login)

    class Meta:
        verbose_name = 'GetCore User'
        verbose_name_plural = 'GetCore Users'
        ordering = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_admin_role(self):
        """Returns True if the user has administrative privileges."""
        return self.role in ('admin', 'manager') or self.is_superuser or self.is_staff

    @property
    def is_floor_staff(self):
        """Returns True if the user is floor staff using PIN login."""
        return self.role in ('cashier', 'waiter')

    def set_pin(self, raw_pin):
        """
        Hash and store a 4-digit PIN.
        Uses Django's built-in password hasher for security.
        """
        from django.contrib.auth.hashers import make_password
        raw_pin = str(raw_pin).strip()
        if not raw_pin.isdigit() or len(raw_pin) != 4:
            raise ValueError('PIN must be exactly 4 numeric digits.')
        self.hashed_pin = make_password(raw_pin)

    def check_pin(self, raw_pin):
        """Verify a raw PIN against the stored hash."""
        from django.contrib.auth.hashers import check_password
        if not self.hashed_pin:
            return False
        return check_password(str(raw_pin), self.hashed_pin)


class UserProfile(models.Model):
    """
    Extended profile data for any user.
    Uses a OneToOne relationship to keep GetCoreUser clean.
    """
    user = models.OneToOneField(
        GetCoreUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    bio = models.TextField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    # Track which terminal / register a staff member is assigned to
    assigned_terminal = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile: {self.user.username}'
