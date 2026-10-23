"""
platform/views.py
GetCore Platform — Staff & Owner Workspace.

Accessible at /platform/... — requires is_staff or is_superuser.
Single-instance: no tenant context.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from pos.models import Sale, Customer
from inventory.models import Product
from settings_app.models import SystemSetting
from .decorators import staff_required
from .forms import PlatformLoginForm, PlatformUserForm
from .models import Notification

User = get_user_model()


# ── Authentication ─────────────────────────────────────────────────────────

def platform_login(request):
    """Login page for platform staff. Uses standard Django password auth."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('platform:dashboard')

    form = PlatformLoginForm()
    if request.method == 'POST':
        form = PlatformLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user and (user.is_staff or user.is_superuser):
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}.')
                return redirect(request.GET.get('next') or 'platform:dashboard')
            else:
                messages.error(request, 'Invalid credentials or insufficient platform privileges.')

    return render(request, 'platform/login.html', {'form': form})


def platform_logout(request):
    logout(request)
    messages.info(request, 'You have been signed out of the platform.')
    return redirect('platform:login')


# ── Dashboard ──────────────────────────────────────────────────────────────

@staff_required
def dashboard(request):
    """System overview — instance-wide KPIs and recent activity."""
    today = timezone.now().date()
    this_month_start = today.replace(day=1)

    # Revenue stats
    today_revenue = Sale.objects.filter(
        created_at__date=today, status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    month_revenue = Sale.objects.filter(
        created_at__date__gte=this_month_start, status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    # Instance counts
    total_users = User.objects.filter(is_superuser=False, is_staff=False, is_active=True).count()
    total_products = Product.objects.filter(is_active=True).count()
    total_customers = Customer.objects.filter(is_active=True).count()

    # 7-day revenue chart
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rev = Sale.objects.filter(
            created_at__date=d, status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        chart_labels.append(d.strftime('%a %d'))
        chart_data.append(float(rev))

    # Recent sales
    recent_sales = Sale.objects.filter(status='completed').order_by('-created_at')[:10]

    sys = SystemSetting.get_settings()

    return render(request, 'platform/dashboard.html', {
        'today_revenue':  today_revenue,
        'month_revenue':  month_revenue,
        'total_users':    total_users,
        'total_products': total_products,
        'total_customers': total_customers,
        'chart_labels':   chart_labels,
        'chart_data':     chart_data,
        'recent_sales':   recent_sales,
        'sys':            sys,
    })


# ── Platform User Management ───────────────────────────────────────────────

@staff_required
def staff_list(request):
    """List all platform staff/superuser accounts."""
    staff = User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True)
    ).order_by('username')
    return render(request, 'platform/staff_list.html', {'staff': staff})


@staff_required
def staff_create(request):
    if request.method == 'POST':
        form = PlatformUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.set_password(form.cleaned_data['password'])
            user.must_change_credentials = False
            user.save()
            messages.success(request, f'Staff account "{user.username}" created.')
            return redirect('platform:staff_list')
    else:
        form = PlatformUserForm()
    return render(request, 'platform/staff_form.html', {'form': form, 'action': 'Create'})


@staff_required
def staff_edit(request, pk):
    user = get_object_or_404(User, pk=pk, is_staff=True)
    if request.method == 'POST':
        form = PlatformUserForm(request.POST, instance=user)
        if form.is_valid():
            u = form.save(commit=False)
            new_pwd = form.cleaned_data.get('password')
            if new_pwd:
                u.set_password(new_pwd)
            u.save()
            messages.success(request, f'Staff account "{user.username}" updated.')
            return redirect('platform:staff_list')
    else:
        form = PlatformUserForm(instance=user)
    return render(request, 'platform/staff_form.html', {
        'form': form, 'action': 'Edit', 'obj': user,
    })


# ── Notifications ──────────────────────────────────────────────────────────

@staff_required
def platform_notifications(request):
    """Platform admin notification centre."""
    notifications = Notification.objects.filter(
        recipient='platform'
    ).order_by('-created_at')[:50]
    Notification.objects.filter(
        recipient='platform', is_read=False
    ).update(is_read=True)
    return render(request, 'platform/notifications.html', {
        'notifications': notifications,
    })


@staff_required
@require_POST
def platform_mark_notification_read(request, pk):
    """AJAX: mark a single platform notification as read."""
    notif = get_object_or_404(Notification, pk=pk, recipient='platform')
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'ok': True})


@staff_required
@require_POST
def platform_mark_all_read(request):
    """Mark all platform admin notifications as read."""
    Notification.objects.filter(recipient='platform', is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


# ── Customer Directory ─────────────────────────────────────────────────────

@staff_required
def all_customers(request):
    """Instance-wide customer directory."""
    q = request.GET.get('q', '').strip()
    credit_filter = request.GET.get('credit', '').strip()

    customers = Customer.objects.filter(is_active=True).order_by('name')

    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    if credit_filter == 'yes':
        customers = customers.filter(is_credit_allowed=True)
    elif credit_filter == 'no':
        customers = customers.filter(is_credit_allowed=False)

    total_count = Customer.objects.filter(is_active=True).count()
    credit_count = Customer.objects.filter(is_active=True, is_credit_allowed=True).count()

    return render(request, 'platform/customers.html', {
        'customers': customers,
        'q': q,
        'credit_filter': credit_filter,
        'total_count': total_count,
        'credit_count': credit_count,
    })


@staff_required
def customer_detail_admin(request, pk):
    """Platform admin view of a single customer's full profile + purchase history."""
    customer = get_object_or_404(Customer, pk=pk)
    sys = SystemSetting.get_settings()
    sales = Sale.objects.filter(
        customer=customer, status='completed'
    ).order_by('-created_at')[:50]
    total_spent = Sale.objects.filter(
        customer=customer, status='completed',
        payment_method__in=['cash', 'mpesa', 'card', 'bank']
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    return render(request, 'platform/customer_detail.html', {
        'customer': customer,
        'sales': sales,
        'total_spent': total_spent,
        'currency': sys.currency_symbol,
    })
