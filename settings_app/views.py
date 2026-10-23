"""settings_app/views.py — Instance settings and notifications."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from users.decorators import login_required, admin_required
from .models import SystemSetting
from .forms import SystemSettingForm


@login_required
@admin_required
def settings_dashboard(request):
    settings_obj = SystemSetting.get_settings()

    if request.method == 'POST':
        form = SystemSettingForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated.')
            return redirect('settings_app:dashboard')
        else:
            messages.error(request, form.errors.as_text())
    else:
        form = SystemSettingForm(instance=settings_obj)

    return render(request, 'settings_app/dashboard.html', {
        'form': form,
        'settings_obj': settings_obj,
    })


# ── In-app Notifications ───────────────────────────────────────────────────────

@login_required
@admin_required
def notifications(request):
    """In-app notification centre."""
    from platform_app.models import Notification
    notification_list = Notification.objects.filter(
        recipient='app'
    ).order_by('-created_at')[:50]
    # Mark all as read when the page is opened
    Notification.objects.filter(
        recipient='app', is_read=False
    ).update(is_read=True)
    sys = SystemSetting.get_settings()
    return render(request, 'settings_app/notifications.html', {
        'notifications': notification_list,
        'currency': sys.currency_symbol,
    })


@login_required
@admin_required
@require_POST
def mark_notification_read(request, pk):
    """AJAX: mark a single notification as read."""
    from platform_app.models import Notification
    notif = get_object_or_404(Notification, pk=pk, recipient='app')
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'ok': True})


@login_required
@admin_required
@require_POST
def mark_all_read(request):
    """Mark all in-app notifications as read."""
    from platform_app.models import Notification
    Notification.objects.filter(recipient='app', is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


# ── Billing stubs (not applicable in single-instance) ─────────────────────────

@login_required
@admin_required
def billing_checkout(request):
    messages.info(request, 'Billing management is not available in this deployment.')
    return redirect('settings_app:dashboard')


@login_required
@admin_required
def billing_success(request):
    messages.info(request, 'Billing management is not available in this deployment.')
    return redirect('settings_app:dashboard')


@login_required
@admin_required
def billing_history(request):
    messages.info(request, 'Billing management is not available in this deployment.')
    return redirect('settings_app:dashboard')
