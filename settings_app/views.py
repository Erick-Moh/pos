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
import calendar
from django.utils import timezone


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
    """
    Payment success page — shown after a successful M-Pesa payment.

    Records which month the payment covers, applying carry-forward logic:
      - If the tenant is already paid for the current month (or beyond),
        the payment rolls forward to the next unpaid month.
    """
    tenant = get_tenant_or_404(request)
    sys = SystemSetting.get_settings(tenant)
    from platform_app.models import TenantPayment, Notification

    today = timezone.now().date()
    current_year, current_month = today.year, today.month

    # ── Determine target month for this payment (carry-forward logic) ─────────
    last_payment = TenantPayment.objects.filter(tenant=tenant).order_by('-year', '-month').first()

    if last_payment and (last_payment.year, last_payment.month) >= (current_year, current_month):
        # Already paid for current month or future — carry forward to next month after last paid
        if last_payment.month == 12:
            target_year, target_month = last_payment.year + 1, 1
        else:
            target_year, target_month = last_payment.year, last_payment.month + 1
    else:
        # No payment yet, or last payment was for a past month — pay for current month
        target_year, target_month = current_year, current_month

    # ── Record the payment ────────────────────────────────────────────────────
    payment, created = TenantPayment.objects.get_or_create(
        tenant=tenant,
        year=target_year,
        month=target_month,
        defaults={
            'amount': tenant.monthly_fee,
            'payment_method': 'mpesa',
            'recorded_by': request.user.username,
        },
    )

    # ── Update tenant's next payment due date ────────────────────────────────
    if target_month == 12:
        next_due_year, next_due_month = target_year + 1, 1
    else:
        next_due_year, next_due_month = target_year, target_month + 1
    # Set due date to the 1st of the following month
    import datetime
    tenant.payment_due_date = datetime.date(next_due_year, next_due_month, 1)
    tenant.save(update_fields=['payment_due_date'])

    # ── In-system notification ────────────────────────────────────────────────
    if created:
        month_name = calendar.month_name[target_month]
        Notification.create_for_tenant(
            tenant=tenant,
            notification_type='payment_confirmed',
            title='Payment Confirmed',
            message=(
                f'Your GetCore subscription payment for {month_name} {target_year} '
                f'(KES {tenant.monthly_fee:,.0f}) has been received. '
                f'Your next payment is due on 1st {calendar.month_name[next_due_month]} {next_due_year}.'
            ),
            action_url=f'/{tenant_slug}/settings/billing/history/',
        )
        Notification.create_for_platform(
            tenant=tenant,
            notification_type='payment_confirmed',
            title=f'Payment Received: {tenant.name}',
            message=(
                f'{tenant.name} ({tenant.reference_code}) has paid KES {tenant.monthly_fee:,.0f} '
                f'for {month_name} {target_year}.'
            ),
            action_url=f'/platform/clients/{tenant.pk}/',
        )

    return render(request, 'settings_app/billing_success.html', {
        'tenant': tenant,
        'tenant_slug': tenant_slug,
        'sys': sys,
        'payment': payment,
        'paid_month': target_month,
        'paid_year': target_year,
        'paid_month_name': calendar.month_name[target_month],
        'next_due_date': tenant.payment_due_date,
    })


@login_required_tenant
@admin_required
def billing_history(request, tenant_slug):
    """
    Billing history for the tenant — shows a monthly summary with payment statuses.

    Statuses:
      paid     — TenantPayment record exists
      current  — This month, not yet paid
      upcoming — Future month, not yet paid
      overdue  — Past month, not yet paid
    """
    tenant = get_tenant_or_404(request)
    sys = SystemSetting.get_settings(tenant)
    from platform_app.models import TenantPayment

    today = timezone.now().date()

    # Build list of months from tenant creation month back to 2 months ahead
    start = tenant.created_at.date().replace(day=1)
    # Show at least 2 months ahead
    end_year = today.year + (1 if today.month >= 11 else 0)
    end_month = (today.month + 2 - 1) % 12 + 1
    if today.month + 2 > 12:
        end_year = today.year + 1
        end_month = today.month + 2 - 12
    else:
        end_year = today.year
        end_month = today.month + 2
    end = timezone.datetime(end_year, end_month, 1).date()

    # Fetch all existing payments for this tenant
    paid_months = {
        (p.year, p.month): p
        for p in TenantPayment.objects.filter(tenant=tenant)
    }

    billing_rows = []
    cursor = start
    while cursor <= end:
        year, month = cursor.year, cursor.month
        payment = paid_months.get((year, month))
        if payment:
            status = 'paid'
        elif (year, month) == (today.year, today.month):
            status = 'current'
        elif cursor > today:
            status = 'upcoming'
        else:
            status = 'overdue'

        billing_rows.append({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'month_abbr': calendar.month_abbr[month],
            'status': status,
            'payment': payment,
            'is_current': (year, month) == (today.year, today.month),
        })

        # Advance to next month
        if month == 12:
            cursor = cursor.replace(year=year + 1, month=1)
        else:
            cursor = cursor.replace(month=month + 1)

    # Newest months first
    billing_rows.reverse()

    total_paid = sum(
        r['payment'].amount for r in billing_rows if r['status'] == 'paid'
    )
    paid_count = sum(1 for r in billing_rows if r['status'] == 'paid')
    overdue_count = sum(1 for r in billing_rows if r['status'] == 'overdue')

    return render(request, 'settings_app/billing_history.html', {
        'tenant': tenant,
        'tenant_slug': tenant_slug,
        'sys': sys,
        'billing_rows': billing_rows,
        'total_paid': total_paid,
        'paid_count': paid_count,
        'overdue_count': overdue_count,
        'today': today,
    })
