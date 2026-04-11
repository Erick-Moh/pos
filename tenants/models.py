"""
tenants/models.py
Tenant model for GetCore multi-tenant ERP.

Each tenant is a distinct business client with their own:
  - Users, Products, Sales, Settings, Reports
  - Accessed via example.com/<tenant_slug>/
"""

from django.db import models


class Tenant(models.Model):
    """
    A single business client (tenant).
    Identified by a unique URL-safe slug that forms the access key.
    """

    PLAN_CHOICES = [
        ('trial',      'Free Trial (14 days)'),
        ('starter',    'Starter'),
        ('business',   'Business'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(
        max_length=200,
        help_text='Business / client name e.g. "Kamau Agrovet Nakuru"'
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
    )
    # Internal reference for platform admin
    reference_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
    )

    # ── Contact ────────────────────────────────────────────────────────────
    owner_name  = models.CharField(max_length=150, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)

    # ── Subscription ───────────────────────────────────────────────────────
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive tenants cannot log in.'
    )
    trial_ends_on = models.DateField(null=True, blank=True)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return f'{self.name} ({self.slug})'

    def save(self, *args, **kwargs):
        # Auto-generate reference code on first save
        if not self.reference_code:
            count = Tenant.objects.count() + 1
            self.reference_code = f'GC-{count:05d}'
            self.slug = f'{self.name.lower().replace(" ", "-")}-{self.reference_code.lower()}'
        super().save(*args, **kwargs)

    @property
    def access_url_path(self):
        return f'/{self.slug}/'
