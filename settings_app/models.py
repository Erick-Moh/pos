"""
settings_app/models.py
Singleton model for global system configuration.
All branding, business info, and theme data lives here.
"""

from django.db import models
from django.core.exceptions import ValidationError


class SystemSetting(models.Model):
    """
    Singleton model — only ONE row should ever exist.
    Stores all business configuration for dynamic branding.
    """


    # ── Business Identity ──────────────────────────────────────────────────
    business_name = models.CharField(
        max_length=200,
        null=True,
        help_text='Displayed in headers, receipts, and reports.'
    )
    business_tagline = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        help_text='Short slogan shown below the business name.'
    )
    logo = models.ImageField(
        upload_to='settings/logos/',
        blank=True,
        null=True,
        help_text='Business logo. Recommended: PNG, 300×100px.'
    )

    # ── Contact Info ───────────────────────────────────────────────────────
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    physical_address = models.TextField(blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True, default='Nairobi')
    country = models.CharField(max_length=100, default='Kenya')

    # ── KRA / Compliance ───────────────────────────────────────────────────
    kra_pin = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name='KRA PIN',
        help_text='Kenya Revenue Authority PIN for eTIMS compliance.'
    )
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=16.00,
        help_text='VAT percentage (e.g. 16.00 for 16%).'
    )
    enable_etims = models.BooleanField(
        default=False,
        verbose_name='Enable eTIMS Integration',
        help_text='Fiscalize transactions via KRA eTIMS API.'
    )

    # ── Theme / Branding ───────────────────────────────────────────────────
    primary_color = models.CharField(
        max_length=7,
        default='#10b981',
        help_text='Hex color code e.g. #0d6efd (Bootstrap Blue).'
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#0d6efd',
        help_text='Hex color code e.g. #198754 (Bootstrap Green).'
    )
    accent_color = models.CharField(
        max_length=7,
        default='#f59e0b',
        help_text='Accent / highlight color.'
    )
    dark_mode = models.BooleanField(default=False)

    # ── Currency ───────────────────────────────────────────────────────────
    currency_code = models.CharField(max_length=5, default='KES')
    currency_symbol = models.CharField(max_length=5, default='KSh')

    # ── Receipt Settings ───────────────────────────────────────────────────
    receipt_footer_text = models.TextField(
        blank=True,
        null=True,
        default='Thank you for your business! | Asante kwa biashara yako!',
        help_text='Text printed at the bottom of every receipt.'
    )
    show_vat_on_receipt = models.BooleanField(default=True)

    # ── Low Stock Alert Threshold ──────────────────────────────────────────
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text='Alert when product quantity falls below this number.'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'System Settings — {self.business_name}'


    @classmethod
    def get_settings(cls):
        """
        Singleton accessor — returns the one SystemSetting row,
        creating it with defaults if it doesn't exist yet.
        """
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj
