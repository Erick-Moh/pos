"""tenants/admin.py"""

from django.contrib import admin
from .models import Tenant
from platform_app.models import TenantPayment


admin.site.register(TenantPayment)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'reference_code', 'plan', 'is_active', 'owner_email', 'created_at']
    list_filter   = ['plan', 'is_active']
    search_fields = ['name', 'slug', 'reference_code', 'owner_email']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['reference_code', 'created_at', 'updated_at']

    fieldsets = [
        ('Identity',      {'fields': ['name', 'slug', 'reference_code', 'business_type']}),
        ('Owner Contact', {'fields': ['owner_name', 'owner_email', 'owner_phone']}),
        ('Subscription',  {'fields': ['plan', 'is_active', 'trial_ends_on', 'load_default_categories', 'load_default_products']}),
        ('Timestamps',    {'fields': ['created_at', 'updated_at']}),
    ]
