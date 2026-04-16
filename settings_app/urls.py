"""settings_app/urls.py"""

from django.urls import path
from . import views

app_name = 'settings_app'

urlpatterns = [
    path('', views.settings_dashboard, name='dashboard'),

    # ── Notifications ─────────────────────────────────────────────────
    path('notifications/',                      views.tenant_notifications,         name='notifications'),
    path('notifications/<int:pk>/read/',        views.tenant_mark_notification_read, name='notification_read'),
    path('notifications/mark-all-read/',        views.tenant_mark_all_read,          name='notifications_mark_all_read'),

    # ── Billing / Checkout ────────────────────────────────────────────
    path('billing/',                            views.billing_checkout,              name='billing_checkout'),
    path('billing/success/',                    views.billing_success,               name='billing_success'),
    path('billing/history/',                    views.billing_history,               name='billing_history'),
]
