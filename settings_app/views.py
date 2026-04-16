"""settings_app/views.py — Tenant-scoped settings."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from users.decorators import login_required_tenant
from django.contrib import messages
from users.decorators import admin_required
from tenants.mixins import get_tenant_or_404
from .models import SystemSetting
from .forms import SystemSettingForm


@login_required_tenant
@admin_required
def settings_dashboard(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    settings_obj = SystemSetting.get_settings(tenant)

    if request.method == 'POST':
        form = SystemSettingForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            s = form.save(commit=False)
            s.tenant = tenant
            s.save()
            messages.success(request, 'Settings updated.')
            return redirect('tenant:settings_app:dashboard', tenant_slug=tenant_slug)
        else:
            messages.error(request, form.errors.as_text())
    else:
        form = SystemSettingForm(instance=settings_obj)

    return render(request, 'settings_app/dashboard.html', {
        'form': form, 'settings_obj': settings_obj, 'tenant_slug': tenant_slug,
    })


# ════════════════════════════════════════════════════════════════════════
#  TENANT NOTIFICATIONS
# ════════════════════════════════════════════════════════════════════════

@login_required_tenant
@admin_required
def tenant_notifications(request, tenant_slug):
    """Tenant admin notification centre."""
    tenant = get_tenant_or_404(request)
    from platform_app.models import Notification
    notifications = Notification.objects.filter(
        tenant=tenant, recipient='tenant'
    ).order_by('-created_at')[:50]
    # Mark all as read when page is opened
    Notification.objects.filter(
        tenant=tenant, recipient='tenant', is_read=False
    ).update(is_read=True)
    sys = SystemSetting.get_settings(tenant)
    return render(request, 'settings_app/notifications.html', {
        'notifications': notifications,
        'tenant_slug': tenant_slug,
        'currency': sys.currency_symbol,
    })


@login_required_tenant
@admin_required
@require_POST
def tenant_mark_notification_read(request, tenant_slug, pk):
    """AJAX: mark a single tenant notification as read."""
    tenant = get_tenant_or_404(request)
    from platform_app.models import Notification
    notif = get_object_or_404(Notification, pk=pk, tenant=tenant, recipient='tenant')
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'ok': True})


@login_required_tenant
@admin_required
@require_POST
def tenant_mark_all_read(request, tenant_slug):
    """Mark all tenant notifications as read."""
    tenant = get_tenant_or_404(request)
    from platform_app.models import Notification
    Notification.objects.filter(
        tenant=tenant, recipient='tenant', is_read=False
    ).update(is_read=True)
    return JsonResponse({'ok': True})


# ════════════════════════════════════════════════════════════════════════
#  TENANT BILLING / CHECKOUT
# ════════════════════════════════════════════════════════════════════════

@login_required_tenant
@admin_required
def billing_checkout(request, tenant_slug):
    """
    Tenant subscription payment page (M-Pesa checkout).
    This is for the tenant paying GetCore maintenance fees — NOT for selling items.
    """
    tenant = get_tenant_or_404(request)
    sys = SystemSetting.get_settings(tenant)
    from django.utils import timezone
    today = timezone.now().date()
    days_remaining = None
    if tenant.trial_ends_on:
        days_remaining = (tenant.trial_ends_on - today).days

    return render(request, 'settings_app/billing_checkout.html', {
        'tenant': tenant,
        'tenant_slug': tenant_slug,
        'sys': sys,
        'today': today,
        'days_remaining': days_remaining,
    })


@login_required_tenant
@admin_required
def billing_success(request, tenant_slug):
    """Payment success page — shown after a successful M-Pesa payment."""
    tenant = get_tenant_or_404(request)
    sys = SystemSetting.get_settings(tenant)
    return render(request, 'settings_app/billing_success.html', {
        'tenant': tenant,
        'tenant_slug': tenant_slug,
        'sys': sys,
    })
