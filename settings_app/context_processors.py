"""
settings_app/context_processors.py
Injects the instance SystemSetting into every template context.
"""

from .models import SystemSetting


def system_settings(request):
    """Injects the singleton SystemSetting as 'sys' into all templates."""
    return {
        'sys': SystemSetting.get_settings(),
    }
