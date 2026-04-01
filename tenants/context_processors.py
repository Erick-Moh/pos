"""
tenants/context_processors.py
Injects the current tenant into every template context.
"""


def tenant(request):
    """Exposes {{ tenant }} in all templates."""
    return {
        'tenant': getattr(request, 'tenant', None),
    }
