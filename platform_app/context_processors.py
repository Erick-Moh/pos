"""
platform_app/context_processors.py
Inject notification data into every template context.
"""


def notifications(request):
    """
    Provides unread notification counts and recent notifications.

    - For tenant views (request.tenant present): injects tenant_notifications.
    - For platform views (request.path starts with /platform/): injects platform_notifications.
    """
    ctx = {
        'tenant_notifications': [],
        'tenant_unread_count': 0,
        'platform_notifications': [],
        'platform_unread_count': 0,
    }

    if not request.user.is_authenticated:
        return ctx

    try:
        from platform_app.models import Notification

        # ── Tenant-side notifications ─────────────────────────────────────
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = Notification.objects.filter(
                tenant=tenant, recipient='tenant'
            ).order_by('-created_at')[:20]
            ctx['tenant_notifications'] = list(qs)
            ctx['tenant_unread_count'] = sum(1 for n in ctx['tenant_notifications'] if not n.is_read)

        # ── Platform-admin notifications ──────────────────────────────────
        if request.path.startswith('/platform/') and (
            request.user.is_staff or request.user.is_superuser
        ):
            qs = Notification.objects.filter(
                recipient='platform'
            ).order_by('-created_at')[:20]
            ctx['platform_notifications'] = list(qs)
            ctx['platform_unread_count'] = sum(1 for n in ctx['platform_notifications'] if not n.is_read)

    except Exception:
        pass  # Never break the page over notifications

    return ctx
