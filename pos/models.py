"""
pos/models.py
Point of Sale models for GetCore ERP.
Includes eTIMS-ready fields for KRA compliance.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


def generate_invoice_number():
    """Generate a unique invoice number: INV-YYYYMMDD-XXXX"""
    today = timezone.now().strftime('%Y%m%d')
    short_uuid = str(uuid.uuid4()).upper()[:6]
    return f'INV-{today}-{short_uuid}'


class Customer(models.Model):
    """Optional customer record for loyalty / credit tracking."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        null=True,   # null during migration; set not-null after data backfill
        db_index=True,
    )

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    kra_pin = models.CharField(max_length=30, blank=True, null=True, verbose_name='Customer KRA PIN')
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.phone or "no phone"})'


class Sale(models.Model):
    """
    A completed transaction / sale.
    eTIMS-ready with fields for KRA invoice number, QR code, and fiscal signature.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        null=True,   # null during migration; set not-null after data backfill
        db_index=True,
    )


    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit / Debit Card'),
        ('credit', 'Store Credit'),
        ('split', 'Split Payment'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('voided', 'Voided'),
        ('refunded', 'Refunded'),
    ]

    # ── Core Fields ────────────────────────────────────────────────────────
    invoice_number = models.CharField(
        max_length=50,
        db_index=True,
        default=generate_invoice_number
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales'
    )
    served_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_served'
    )

    # ── Financials ─────────────────────────────────────────────────────────
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── Payment ────────────────────────────────────────────────────────────
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    amount_tendered = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    change_given = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mpesa_transaction_code = models.CharField(max_length=50, blank=True, null=True)
    card_reference = models.CharField(max_length=50, blank=True, null=True)

    # ── eTIMS / KRA Compliance Fields ──────────────────────────────────────
    kra_invoice_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='KRA Invoice Number',
        help_text='Returned by KRA eTIMS after successful fiscalization.'
    )
    qr_code_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='QR Code URL',
        help_text='KRA-generated QR code URL for receipt verification.'
    )
    fiscal_signature = models.TextField(
        blank=True,
        null=True,
        verbose_name='Fiscal Signature',
        help_text='Cryptographic signature from KRA eTIMS.'
    )
    is_fiscalized = models.BooleanField(default=False)

    # ── Status & Notes ─────────────────────────────────────────────────────
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True, null=True)
    void_reason = models.TextField(blank=True, null=True)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice_number} | {self.total_amount} | {self.payment_method}'

    def calculate_totals(self):
        """
        Recalculate subtotal, VAT, discounts, and total from line items.
        Call this before saving when items have been added/changed.
        """
        from decimal import Decimal
        items = self.items.all()
        self.subtotal = sum(item.line_total for item in items)

        # Apply percentage discount first
        if self.discount_percent > 0:
            self.discount_amount = self.subtotal * (self.discount_percent / 100)

        # VAT calculation (16% default — fetched from SystemSetting in view)
        taxable_amount = self.subtotal - self.discount_amount
        # VAT is calculated in the view using SystemSetting.vat_rate
        self.total_amount = taxable_amount + self.vat_amount
        self.change_given = max(Decimal('0'), self.amount_tendered - self.total_amount)


class SaleItem(models.Model):
    """
    A single line item within a Sale.
    Captures the price at time of sale to preserve historical accuracy.
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='sale_items'
    )

    # Snapshot prices at time of sale
    product_name = models.CharField(max_length=200)  # Snapshot
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_vat_exempt = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} x {self.product_name} @ {self.unit_price}'

    def save(self, *args, **kwargs):
        # Snapshot product name for historical records
        if not self.product_name:
            self.product_name = self.product.name
        # Calculate line total
        self.line_total = (self.unit_price * self.quantity) - self.discount_amount
        super().save(*args, **kwargs)
