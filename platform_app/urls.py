"""platform/urls.py — GetCore platform staff workspace."""

from django.urls import path
from . import views

app_name = 'platform'

urlpatterns = [
    # Auth
    path('login/',   views.platform_login,  name='login'),
    path('logout/',  views.platform_logout, name='logout'),

    # Dashboard
    path('',         views.dashboard,       name='dashboard'),

    # Tenant (client) management
    path('clients/',                      views.tenant_list,    name='tenant_list'),
    path('clients/new/',                  views.tenant_create,  name='tenant_create'),
    path('clients/<int:pk>/',             views.tenant_detail,  name='tenant_detail'),
    path('clients/<int:pk>/edit/',        views.tenant_edit,    name='tenant_edit'),
    path('clients/<int:pk>/toggle/',      views.tenant_toggle,  name='tenant_toggle'),

    # Platform staff management
    path('staff/',                        views.staff_list,     name='staff_list'),
    path('staff/new/',                    views.staff_create,   name='staff_create'),
    path('staff/<int:pk>/edit/',          views.staff_edit,     name='staff_edit'),

    # ── Platform Notifications ────────────────────────────────────────
    path('notifications/',                              views.platform_notifications,             name='notifications'),
    path('notifications/<int:pk>/read/',               views.platform_mark_notification_read,    name='notification_read'),
    path('notifications/mark-all-read/',               views.platform_mark_all_read,             name='notifications_mark_all_read'),
]
