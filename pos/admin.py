"""pos/admin.py"""

from django.contrib import admin
from .models import Sale, SaleItem, Customer


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['product_name', 'unit_price', 'quantity', 'line_total']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'total_amount', 'payment_method', 'status', 'served_by', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['invoice_number', 'mpesa_transaction_code']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    inlines = [SaleItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'is_active']
    search_fields = ['name', 'phone']
