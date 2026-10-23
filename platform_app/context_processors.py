"""
platform_app/context_processors.py
Inject notification data into every template context.
"""


def notifications(request):
    """
    Provides unread notification counts and recent notifications.

    - 'app_notifications'      → in-app bell (visible to all authenticated users)
    - 'platform_notifications' → /platform/ admin bell (staff/superuser only)
    """
    ctx = {
        'app_notifications':      [],
        'app_unread_count':       0,
        'platform_notifications': [],
        'platform_unread_count':  0,
    }

    if not request.user.is_authenticated:
        return ctx

    try:
        from platform_app.models import Notification

        # In-app notifications for all authenticated users
        qs = Notification.objects.filter(
            recipient='app'
        ).order_by('-created_at')[:20]
        ctx['app_notifications'] = list(qs)
        ctx['app_unread_count'] = sum(1 for n in ctx['app_notifications'] if not n.is_read)

        # Platform-admin notifications (staff/superuser in /platform/)
        if request.path.startswith('/platform/') and (
            request.user.is_staff or request.user.is_superuser
        ):
            qs = Notification.objects.filter(
                recipient='platform'
            ).order_by('-created_at')[:20]
            ctx['platform_notifications'] = list(qs)
            ctx['platform_unread_count'] = sum(
                1 for n in ctx['platform_notifications'] if not n.is_read
            )

    except Exception:
        pass  # Never break the page over notifications

    return ctx
