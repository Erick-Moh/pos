"""
GetCore — Master URL Configuration
Single-tenant, no slug prefix.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from core.pwa_views import service_worker, manifest
from users import views as user_views
from pos import print_api as pos_print_api

print_api_patterns = [
    path('api/print/heartbeat/',                     pos_print_api.heartbeat,  name='print_heartbeat'),
    path('api/print/jobs/',                          pos_print_api.poll_jobs,  name='print_poll'),
    path('api/print/jobs/<int:job_id>/ack/',         pos_print_api.job_ack,    name='print_ack'),
    path('api/print/jobs/<int:job_id>/done/',        pos_print_api.job_done,   name='print_done'),
    path('api/print/jobs/<int:job_id>/fail/',        pos_print_api.job_fail,   name='print_fail'),
]

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('platform/',     include('platform_app.urls', namespace='platform')),

    # Auth
    path('login/',        user_views.login_staff, name='login'),
    path('login/admin/',  user_views.login_admin,  name='login_admin'),
    path('logout/',       user_views.logout_view,  name='logout'),

    # App modules
    path('pos/',       include('pos.urls',          namespace='pos')),
    path('inventory/', include('inventory.urls',    namespace='inventory')),
    path('finance/',   include('finance.urls',      namespace='finance')),
    path('settings/',  include('settings_app.urls', namespace='settings_app')),
    path('users/',     include('users.urls',        namespace='users')),

    # PWA
    path('service-worker.js', service_worker),
    path('manifest.json',     manifest),

    # Root
    path('', lambda r: redirect('pos:dashboard'), name='home'),
] + print_api_patterns

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
