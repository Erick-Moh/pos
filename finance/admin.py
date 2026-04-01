"""finance/admin.py"""

from django.contrib import admin
from .models import DailySummary, MonthlySummary


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_sales', 'total_transactions', 'gross_profit', 'is_closed']
    list_filter = ['is_closed']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MonthlySummary)
class MonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ['year', 'month', 'total_revenue', 'gross_profit', 'total_transactions']
