"""settings_app/admin.py"""

from django.contrib import admin
from .models import SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'kra_pin', 'currency_code', 'updated_at']

    def has_add_permission(self, request):
        # Only allow adding if no instance exists yet (singleton enforcement)
        return not SystemSetting.objects.exists()
