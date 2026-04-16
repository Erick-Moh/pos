"""
GetCore ERP — Master URL Configuration
Multi-tenant routing: /<tenant_slug>/<app>/...
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views as core_views
from tenants.manifest_views import service_worker, manifest

tenant_urlpatterns = [
    path('users/', include('users.urls', namespace='users')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('pos/', include('pos.urls', namespace='pos')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('settings/', include('settings_app.urls', namespace='settings_app')),
]

from pos import print_api as pos_print_api

# ── Global print agent API (token-auth, no tenant scope) ─────────────────────
# These are accessed by the local print agent using only its device token.
print_api_patterns = [
    path('api/print/heartbeat/',                     pos_print_api.heartbeat,  name='print_heartbeat'),
    path('api/print/jobs/',                          pos_print_api.poll_jobs,  name='print_poll'),
    path('api/print/jobs/<int:job_id>/ack/',         pos_print_api.job_ack,    name='print_ack'),
    path('api/print/jobs/<int:job_id>/done/',        pos_print_api.job_done,   name='print_done'),
    path('api/print/jobs/<int:job_id>/fail/',        pos_print_api.job_fail,   name='print_fail'),
]

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('platform/', include('platform_app.urls', namespace='platform')),
    path('', core_views.landing_page, name='landing'),
    path('service-worker.js', service_worker),
    path('<slug:tenant_slug>/manifest.json', manifest),
    path('<slug:tenant_slug>/', include((tenant_urlpatterns, 'tenant'), namespace='tenant')),
] + print_api_patterns

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
