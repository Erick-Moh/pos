"""
inventory/models.py
Core inventory models for GetCore ERP.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    """Product category with optional parent (nested categories)."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        null=True,   # null during migration; set not-null after data backfill
        db_index=True,
    )

    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Bootstrap icon class, e.g. bi-box-seam'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
        unique_together = [['tenant', 'name']]

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} → {self.name}'
        return self.name

    def get_full_path(self):
        if self.parent:
            return f'{self.parent.name} / {self.name}'
        return self.name


class Supplier(models.Model):
    """Product supplier / vendor record."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        null=True,   # null during migration; set not-null after data backfill
        db_index=True,
    )

    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    kra_pin = models.CharField(max_length=30, blank=True, null=True, verbose_name='Supplier KRA PIN')
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Core product/stock item model.
    Tracks buying price, selling price, stock level, and reorder alerts.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        null=True,   # null during migration; set not-null after data backfill
        db_index=True,
    )

    UNIT_CHOICES = [
        ('pcs', 'Pieces'),
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('l', 'Litres'),
        ('ml', 'Millilitres'),
        ('box', 'Box'),
        ('crate', 'Crate'),
        ('dozen', 'Dozen'),
        ('pack', 'Pack'),
    ]

    # ── Identification ─────────────────────────────────────────────────────
    name = models.CharField(max_length=200)
    sku = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name='SKU / Barcode',
        help_text='Stock Keeping Unit or barcode number.'
    )
    barcode = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    # ── Classification ─────────────────────────────────────────────────────
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs')

    # ── Pricing ────────────────────────────────────────────────────────────
    buying_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text='Cost price from supplier.'
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text='Retail price charged to customer.'
    )
    wholesale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Optional wholesale / bulk price.'
    )

    # ── Stock Levels ───────────────────────────────────────────────────────
    quantity_in_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=10,
        help_text='Alert when stock falls below this level.'
    )
    max_stock_level = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ── VAT / Tax ──────────────────────────────────────────────────────────
    is_vat_exempt = models.BooleanField(default=False)

    # ── Status ─────────────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_service = models.BooleanField(
        default=False,
        help_text='If True, stock tracking is disabled (e.g. labour, service fee).'
    )

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku or "no-sku"})'

    @property
    def is_low_stock(self):
        """Returns True if stock is at or below the reorder level."""
        return not self.is_service and self.quantity_in_stock <= self.reorder_level

    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.buying_price and self.selling_price and self.buying_price > 0:
            profit = self.selling_price - self.buying_price
            return round((profit / self.selling_price) * 100, 1)
        return 0

    @property
    def stock_value(self):
        """Total stock value at buying price."""
        return self.quantity_in_stock * self.buying_price


class StockMovement(models.Model):
    """
    Audit trail for all stock changes (purchases, sales, adjustments, damages).
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        null=True,   # null during migration; set not-null after data backfill
        db_index=True,
    )

    MOVEMENT_TYPES = [
        ('purchase', 'Purchase / Stock In'),
        ('sale', 'Sale / Stock Out'),
        ('adjustment', 'Manual Adjustment'),
        ('return', 'Customer Return'),
        ('damage', 'Damaged / Write-off'),
        ('transfer', 'Stock Transfer'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Positive for stock in, negative for stock out.'
    )
    quantity_before = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Invoice number, PO number, or sale reference.'
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.movement_type.upper()} | {self.product.name} | Qty: {self.quantity}'

    def save(self, *args, **kwargs):
        """Auto-update product stock level when a movement is saved."""
        if not self.pk:  # Only on creation
            self.quantity_before = self.product.quantity_in_stock
            self.product.quantity_in_stock += self.quantity
            self.quantity_after = self.product.quantity_in_stock
            self.product.save()
        super().save(*args, **kwargs)
