"""
finance/models.py
Finance and reporting models for GetCore ERP.
Stores daily/monthly/yearly aggregates for fast reporting.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class DailySummary(models.Model):
    """
    Close-of-Business (COB) snapshot for a single day.
    Auto-generated or manually triggered by the manager.
    """

    date = models.DateField()

    # ── Revenue Breakdown ──────────────────────────────────────────────────
    total_sales = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_transactions = models.PositiveIntegerField(default=0)
    total_vat_collected = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_discounts_given = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── Payment Method Breakdown ───────────────────────────────────────────
    cash_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mpesa_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    card_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Cash actually received from credit repayments on this day
    credit_repayments_received = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── Cost & Profit ──────────────────────────────────────────────────────
    total_cost_of_goods = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    # ── Till Reconciliation ────────────────────────────────────────────────
    expected_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    actual_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Manually entered by manager during till reconciliation.'
    )
    cash_variance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Difference between expected and actual cash (actual - expected).'
    )

    # ── Voided Sales ───────────────────────────────────────────────────────
    voided_count = models.PositiveIntegerField(default=0)
    voided_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── Meta ───────────────────────────────────────────────────────────────
    is_closed = models.BooleanField(default=False, help_text='True once COB is finalized.')
    notes = models.TextField(blank=True, null=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summaries'
        ordering = ['-date']
        unique_together = [['date']]

    def __str__(self):
        return f'COB Report: {self.date} | KSh {self.total_sales}'

    def calculate_variance(self):
        if self.actual_cash is not None:
            self.cash_variance = self.actual_cash - self.expected_cash


class MonthlySummary(models.Model):
    """Aggregate monthly performance snapshot."""

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()  # 1-12

    total_revenue = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_transactions = models.PositiveIntegerField(default=0)
    total_cost_of_goods = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_vat = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    cash_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    mpesa_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    card_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    best_selling_product = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['year', 'month']]
        ordering = ['-year', '-month']

    def __str__(self):
        import calendar
        month_name = calendar.month_name[self.month]
        return f'{month_name} {self.year} | KSh {self.total_revenue}'

    @property
    def profit_margin_percent(self):
        if self.total_revenue and self.total_revenue > 0:
            return round((self.gross_profit / self.total_revenue) * 100, 1)
        return 0
