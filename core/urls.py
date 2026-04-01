"""
GetCore ERP — Master URL Configuration
Multi-tenant routing: /<tenant_slug>/<app>/...
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views as core_views

tenant_urlpatterns = [
    path('users/', include('users.urls', namespace='users')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('pos/', include('pos.urls', namespace='pos')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('settings/', include('settings_app.urls', namespace='settings_app')),
]

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('platform/', include('platform_app.urls', namespace='platform')),
    path('', core_views.landing_page, name='landing'),
    path('<slug:tenant_slug>/', include((tenant_urlpatterns, 'tenant'), namespace='tenant')),
]

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
