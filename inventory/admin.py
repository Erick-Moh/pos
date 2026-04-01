"""inventory/admin.py"""

from django.contrib import admin
from .models import Category, Supplier, Product, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'is_active']
    search_fields = ['name', 'contact_person']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'selling_price', 'quantity_in_stock', 'is_low_stock', 'is_active']
    list_filter = ['category', 'is_active', 'is_service']
    search_fields = ['name', 'sku', 'barcode']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'quantity_before', 'quantity_after', 'created_at']
    list_filter = ['movement_type']
    readonly_fields = ['quantity_before', 'quantity_after', 'created_at']
