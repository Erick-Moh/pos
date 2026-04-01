"""
settings_app/context_processors.py
Injects tenant-scoped SystemSetting into every template context.
"""

from .models import SystemSetting


def system_settings(request):
    """
    Global context processor — tenant-aware.
    Uses request.tenant (set by TenantMiddleware) to fetch the correct settings.
    Falls back to defaults for the root landing page (tenant=None).
    """
    tenant = getattr(request, 'tenant', None)
    settings_obj = SystemSetting.get_settings(tenant)
    return {
        'sys': settings_obj,
    }
