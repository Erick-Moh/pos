"""
platform_app/models.py
Platform-level models: in-system notifications for tenants and platform admins,
and tenant payment records for subscription billing.
"""

from django.db import models
from django.utils import timezone
import calendar


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


# ════════════════════════════════════════════════════════════════════════════════
#  TENANT PAYMENT
# ════════════════════════════════════════════════════════════════════════════════

class TenantPayment(models.Model):
    """
    Records each monthly maintenance fee payment made by a tenant.

    Carry-forward logic (enforced in billing_success view):
      - If the tenant's last payment already covers the current month,
        the new payment is applied to the following month automatically.
    """

    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('bank',  'Bank Transfer'),
        ('cash',  'Cash'),
        ('other', 'Other'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    year = models.IntegerField(
        help_text='Calendar year the payment covers (e.g. 2026).'
    )
    month = models.IntegerField(
        help_text='Month number the payment covers: 1=January … 12=December.'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text='Amount paid (KES).',
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa',
    )
    mpesa_reference = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='M-Pesa transaction code / confirmation number.',
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Username of the user who recorded the payment.',
    )

    class Meta:
        ordering = ['-year', '-month']
        unique_together = [('tenant', 'year', 'month')]
        verbose_name = 'Tenant Payment'
        verbose_name_plural = 'Tenant Payments'
        indexes = [
            models.Index(fields=['tenant', 'year', 'month']),
        ]

    def __str__(self):
        return f'{self.tenant.name} — {self.month_name} {self.year} (KES {self.amount})'

    @property
    def month_name(self):
        """Full month name, e.g. 'April'."""
        return calendar.month_name[self.month]

    @property
    def month_abbr(self):
        """Abbreviated month name, e.g. 'Apr'."""
        return calendar.month_abbr[self.month]
