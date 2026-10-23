"""
platform_app/models.py
In-system notification model for GetCore.
"""

from django.db import models


class Notification(models.Model):
    """
    In-system notification record.

    recipient = 'app'       → shown to business admin in the main app bell
    recipient = 'platform'  → shown to platform staff in /platform/ bell
    """

    RECIPIENT_CHOICES = [
        ('app',      'Application'),
        ('platform', 'Platform Admin'),
    ]

    TYPE_CHOICES = [
        ('welcome',            'Welcome'),
        ('payment_confirmed',  'Payment Confirmed'),
        ('account_reactivated','Account Reactivated'),
        ('info',               'Info'),
        ('warning',            'Warning'),
    ]

    ICON_MAP = {
        'welcome':             ('bi-stars',             'text-primary'),
        'payment_confirmed':   ('bi-patch-check-fill',  'text-success'),
        'account_reactivated': ('bi-check-circle-fill', 'text-success'),
        'info':                ('bi-info-circle-fill',  'text-info'),
        'warning':             ('bi-exclamation-triangle-fill', 'text-warning'),
    }

    recipient = models.CharField(
        max_length=20,
        choices=RECIPIENT_CHOICES,
        default='app',
        db_column='recipient',
    )
    notification_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='notif_recipient_read_idx'),
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
    def create_for_app(cls, notification_type, title, message, action_url=None):
        """Create a notification shown in the main app notification bell."""
        return cls.objects.create(
            recipient='app',
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
        )

    @classmethod
    def create_for_platform(cls, notification_type, title, message, action_url=None):
        """Create a notification shown in the /platform/ admin bell."""
        return cls.objects.create(
            recipient='platform',
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
        )
