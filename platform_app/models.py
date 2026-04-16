"""
platform_app/models.py
Platform-level models: in-system notifications for tenants and platform admins.
"""

from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """
    In-system notification record.

    recipient = 'tenant'   → shown to the tenant's admin user in base.html bell
    recipient = 'platform' → shown to platform staff in platform/base.html bell
    """

    RECIPIENT_CHOICES = [
        ('tenant',   'Tenant'),
        ('platform', 'Platform Admin'),
    ]

    TYPE_CHOICES = [
        # Tenant-facing
        ('welcome',            'Welcome to GetCore'),
        ('trial_expiry_5d',    'Trial Expiring in 5 Days'),
        ('trial_expiry_2d',    'Trial Expiring in 2 Days'),
        ('trial_ended',        'Trial Ended / Account Locked'),
        ('payment_due',        'Maintenance Fee Due'),
        ('payment_overdue',    'Payment Overdue'),
        ('account_deactivated','Account Deactivated'),
        ('account_reactivated','Account Reactivated'),
        ('payment_confirmed',  'Payment Confirmed'),
        # Platform-facing
        ('new_tenant',         'New Client Signup'),
        ('payment_defaulted',  'Client Payment Defaulted'),
        ('trial_expired_admin','Client Trial Expired'),
    ]

    ICON_MAP = {
        'welcome':             ('bi-stars',                  'text-primary'),
        'trial_expiry_5d':     ('bi-hourglass-split',        'text-warning'),
        'trial_expiry_2d':     ('bi-hourglass-bottom',       'text-orange'),
        'trial_ended':         ('bi-lock-fill',              'text-danger'),
        'payment_due':         ('bi-calendar-event',         'text-warning'),
        'payment_overdue':     ('bi-exclamation-triangle-fill','text-danger'),
        'account_deactivated': ('bi-slash-circle-fill',      'text-danger'),
        'account_reactivated': ('bi-check-circle-fill',      'text-success'),
        'payment_confirmed':   ('bi-patch-check-fill',       'text-success'),
        'new_tenant':          ('bi-buildings',              'text-primary'),
        'payment_defaulted':   ('bi-currency-dollar',        'text-danger'),
        'trial_expired_admin': ('bi-hourglass-bottom',       'text-warning'),
    }

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
        help_text='Null for platform-wide admin notifications.',
    )
    recipient = models.CharField(max_length=20, choices=RECIPIENT_CHOICES, default='tenant')
    notification_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=300, blank=True, null=True,
                                  help_text='Optional URL for a CTA button inside the notification.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'recipient', 'is_read']),
        ]

    def __str__(self):
        return f'[{self.get_recipient_display()}] {self.title} ({"read" if self.is_read else "unread"})'

    @property
    def icon(self):
        return self.ICON_MAP.get(self.notification_type, ('bi-bell-fill', 'text-secondary'))[0]

    @property
    def icon_color(self):
        return self.ICON_MAP.get(self.notification_type, ('bi-bell-fill', 'text-secondary'))[1]

    @classmethod
    def create_for_tenant(cls, tenant, notification_type, title, message, action_url=None):
        """Convenience: create a tenant-facing notification."""
        return cls.objects.create(
            tenant=tenant,
            recipient='tenant',
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
        )

    @classmethod
    def create_for_platform(cls, tenant, notification_type, title, message, action_url=None):
        """Convenience: create a platform-admin notification (optionally linked to a tenant)."""
        return cls.objects.create(
            tenant=tenant,
            recipient='platform',
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
        )
