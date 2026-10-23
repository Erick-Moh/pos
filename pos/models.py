"""
pos/models.py
Point of Sale models for GetCore ERP.
Includes eTIMS-ready fields for KRA compliance.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


def generate_invoice_number():
    """Generate a unique invoice number: INV-YYYYMMDD-XXXX"""
    today = timezone.now().strftime('%Y%m%d')
    short_uuid = str(uuid.uuid4()).upper()[:6]
    return f'INV-{today}-{short_uuid}'


def generate_device_token():
    """Generate a unique token for a print device."""
    return uuid.uuid4().hex


class Customer(models.Model):
    """Optional customer record for loyalty / credit tracking."""

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    kra_pin = models.CharField(max_length=30, blank=True, null=True, verbose_name='Customer KRA PIN')
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text='Internal notes about this customer.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Credit Settings ────────────────────────────────────────────────────
    is_credit_allowed = models.BooleanField(
        default=False,
        help_text='Allow this customer to purchase on credit (pay later). Walk-in customers cannot use credit.'
    )
    credit_limit = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0'),
        help_text='Maximum credit balance allowed (0 = unlimited if credit is enabled)'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.phone or "no phone"})'

    @property
    def outstanding_balance(self):
        """True outstanding amount: sum of credit portions minus all repayments made."""
        from django.db.models import Sum
        unpaid_sales = self.sales.filter(
            credit_portion__gt=0, credit_paid=False, status='completed'
        )
        total_credit = unpaid_sales.aggregate(total=Sum('credit_portion'))['total'] or Decimal('0')
        total_repaid = CreditRepayment.objects.filter(
            sale__in=unpaid_sales
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return max(Decimal('0'), total_credit - total_repaid)

    @property
    def available_credit(self):
        """How much more credit this customer can use (0 credit_limit = unlimited)."""
        if self.credit_limit == Decimal('0'):
            return None  # Unlimited
        return max(Decimal('0'), self.credit_limit - self.outstanding_balance)


class Sale(models.Model):
    """
    A completed transaction / sale.
    eTIMS-ready with fields for KRA invoice number, QR code, and fiscal signature.
    """


    PAYMENT_METHOD_CHOICES = [
        ('cash',   'Cash'),
        ('mpesa',  'M-Pesa'),
        ('card',   'Credit / Debit Card'),
        ('credit', 'Store Credit (Pay Later)'),
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

    # ── Credit / Pay-Later Fields ──────────────────────────────────────────
    # NOTE: credit_paid is kept as a DB field for fast querying.
    # It is set to True automatically when total repayments >= credit_portion.
    credit_portion = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0'),
        help_text='Amount deferred to credit (0 = no credit component on this sale).'
    )
    credit_due_date = models.DateField(
        null=True, blank=True,
        help_text='Date by which the customer must settle this credit sale.'
    )
    credit_paid = models.BooleanField(
        default=False,
        help_text='True once the customer has repaid this credit sale.'
    )
    credit_paid_at = models.DateTimeField(null=True, blank=True)
    credit_paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='credit_payments_recorded',
        help_text='Staff member who recorded the credit repayment.'
    )
    credit_payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True,
        help_text='How the credit was eventually settled.'
    )
    credit_payment_reference = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='M-Pesa transaction code or other payment reference for the credit settlement.'
    )

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

    @property
    def amount_repaid(self):
        from django.db.models import Sum
        return self.repayments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @property
    def balance_due(self):
        if self.credit_portion <= Decimal('0'):
            return Decimal('0')
        return max(Decimal('0'), self.credit_portion - self.amount_repaid)

    @property
    def is_fully_paid(self):
        return self.balance_due <= Decimal('0')

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


# ═══════════════════════════════════════════════════════════════════════════════
#  CREDIT REPAYMENT  (partial / full payment against a credit sale)
# ═══════════════════════════════════════════════════════════════════════════════

class CreditRepayment(models.Model):
    """
    Records a single payment (partial or full) against a credit sale.
    Multiple repayments can exist per Sale. When their sum reaches
    Sale.total_amount, the sale is automatically marked credit_paid=True.
    """

    PAYMENT_METHOD_CHOICES = [
        ('cash',  'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card',  'Credit / Debit Card'),
    ]

    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name='repayments'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    reference = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='M-Pesa code, cheque number, or other payment reference.'
    )
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='credit_repayments_recorded'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at']
        verbose_name = 'Credit Repayment'
        verbose_name_plural = 'Credit Repayments'

    def __str__(self):
        return f'Repayment {self.amount} on {self.sale.invoice_number} @ {self.recorded_at:%d %b %Y}'


# ═══════════════════════════════════════════════════════════════════════════════
#  PRINT DEVICE + PRINT JOB  (local print agent bridge)
# ═══════════════════════════════════════════════════════════════════════════════

class PrintDevice(models.Model):
    """
    Represents one installation of the GetCore Print Agent on a local computer.
    Each device holds a unique token used to authenticate polling requests.
    """
    name = models.CharField(
        max_length=100,
        help_text='Friendly name, e.g. "Front Counter Printer" or "Kitchen Printer".',
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_device_token,
        help_text='Secret token the local agent uses to authenticate. Never share this.',
    )
    printer_name = models.CharField(
        max_length=200,
        blank=True, null=True,
        help_text='Name of the locally detected printer as reported by the agent.',
    )
    os_info = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text='OS string reported by the agent, e.g. "Windows 11 Home".',
    )
    agent_version = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Version of the GetCore Print Agent installed.',
    )
    is_online = models.BooleanField(
        default=False,
        help_text='True when the agent sent a heartbeat within the last 90 seconds.',
    )
    last_seen = models.DateTimeField(
        null=True, blank=True,
        help_text='Timestamp of the last heartbeat received from this device.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Disable to stop this device from receiving print jobs.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Print Device'
        verbose_name_plural = 'Print Devices'

    def __str__(self):
        status = 'online' if self.is_online else 'offline'
        return f'{self.name} — {status}'

    def refresh_online_status(self):
        """Mark device offline if last heartbeat > 90 seconds ago."""
        if self.last_seen:
            age = (timezone.now() - self.last_seen).total_seconds()
            if age > 90 and self.is_online:
                self.is_online = False
                self.save(update_fields=['is_online'])
        return self.is_online

    @property
    def is_ready(self):
        """True when the agent is online AND has detected a printer."""
        self.refresh_online_status()
        return self.is_online and bool(self.printer_name)


class PrintJob(models.Model):
    """
    A receipt print job queued by Django and consumed by the local Print Agent.
    """
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('sent',     'Sent to Agent'),
        ('printed',  'Printed'),
        ('failed',   'Failed'),
        ('cancelled','Cancelled'),
    ]

    device = models.ForeignKey(
        PrintDevice,
        on_delete=models.CASCADE,
        related_name='print_jobs',
    )
    sale = models.ForeignKey(
        'pos.Sale',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='print_jobs',
        help_text='The sale this receipt belongs to (optional).',
    )
    # The receipt content sent to the agent.
    # Stored as pre-formatted text so the agent can print without any rendering.
    receipt_text = models.TextField(
        help_text='Pre-formatted plain text receipt ready to send to the printer.',
    )
    copies = models.PositiveSmallIntegerField(
        default=1,
        help_text='Number of copies to print.',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
    )
    error_message = models.TextField(
        blank=True, null=True,
        help_text='Error detail if printing failed.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    printed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Print Job'
        verbose_name_plural = 'Print Jobs'
        indexes = [
            models.Index(fields=['device', 'status', 'created_at']),
        ]

    def __str__(self):
        return f'PrintJob #{self.pk} → {self.device.name} [{self.status}]'
