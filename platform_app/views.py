"""
platform/views.py
GetCore Platform — Staff & Owner Workspace.

All views here are accessible at /platform/... and require is_staff or is_superuser.
No tenant context — this is the cross-tenant management layer.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from decimal import Decimal

from tenants.models import Tenant
from pos.models import Sale
from inventory.models import Product
from settings_app.models import SystemSetting
from .decorators import staff_required
from .forms import (
    PlatformLoginForm, TenantForm, PlatformUserForm,
)
from .tasks import send_tenant_welcome_email

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
    """Platform overview — cross-tenant KPIs and recent activity."""
    today = timezone.now().date()
    this_month_start = today.replace(day=1)

    # Tenant stats
    total_tenants  = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()
    new_this_month = Tenant.objects.filter(created_at__date__gte=this_month_start).count()

    # Cross-tenant revenue (today + this month)
    today_revenue = Sale.objects.filter(
        created_at__date=today, status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    month_revenue = Sale.objects.filter(
        created_at__date__gte=this_month_start, status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    # Total users across all tenants (excluding superusers)
    total_users = User.objects.filter(is_superuser=False).count()

    # Total products across all tenants
    total_products = Product.objects.filter(is_active=True).count()

    # 7-day revenue chart (all tenants combined)
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rev = Sale.objects.filter(
            created_at__date=d, status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        chart_labels.append(d.strftime('%a %d'))
        chart_data.append(float(rev))

    # Recent tenants
    recent_tenants = Tenant.objects.order_by('-created_at')[:5]

    # Top tenants by revenue this month
    top_tenants = (
        Sale.objects
        .filter(created_at__date__gte=this_month_start, status='completed')
        .values('tenant__name', 'tenant__slug')
        .annotate(revenue=Sum('total_amount'), tx_count=Count('id'))
        .order_by('-revenue')[:8]
    )

    return render(request, 'platform/dashboard.html', {
        'total_tenants':  total_tenants,
        'active_tenants': active_tenants,
        'new_this_month': new_this_month,
        'today_revenue':  today_revenue,
        'month_revenue':  month_revenue,
        'total_users':    total_users,
        'total_products': total_products,
        'chart_labels':   chart_labels,
        'chart_data':     chart_data,
        'recent_tenants': recent_tenants,
        'top_tenants':    top_tenants,
    })


# ── Tenant Management ──────────────────────────────────────────────────────

@staff_required
def tenant_list(request):
    q = request.GET.get('q', '')
    plan = request.GET.get('plan', '')
    status = request.GET.get('status', '')

    tenants = Tenant.objects.annotate(
        user_count=Count('users', distinct=True),
    ).order_by('name')

    if q:
        tenants = tenants.filter(
            Q(name__icontains=q) | Q(slug__icontains=q) |
            Q(owner_name__icontains=q) | Q(owner_email__icontains=q)
        )
    if plan:
        tenants = tenants.filter(plan=plan)
    if status == 'active':
        tenants = tenants.filter(is_active=True)
    elif status == 'inactive':
        tenants = tenants.filter(is_active=False)

    return render(request, 'platform/tenant_list.html', {
        'tenants': tenants, 'q': q, 'plan_filter': plan, 'status_filter': status,
        'plan_choices': Tenant.PLAN_CHOICES,
    })


@staff_required
def tenant_create(request):
    if request.method == 'POST':
        form = TenantForm(request.POST)
        if form.is_valid():
            tenant = form.save()
            # Auto-create SystemSetting for this tenant
            SystemSetting.get_settings(tenant)
            send_tenant_welcome_email.delay(
                tenant_name=tenant.name,
                contact_email=tenant.owner_email,
                contact_name=tenant.owner_name,
            )
            messages.success(request, f'Client "{tenant.name}" created. Access key: /{tenant.slug}/')
            return redirect('platform:tenant_detail', pk=tenant.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TenantForm()
    return render(request, 'platform/tenant_form.html', {'form': form, 'action': 'Create'})


@staff_required
def tenant_edit(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    if request.method == 'POST':
        form = TenantForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{tenant.name}" updated.')
            return redirect('platform:tenant_detail', pk=pk)
    else:
        form = TenantForm(instance=tenant)
    return render(request, 'platform/tenant_form.html', {
        'form': form, 'action': 'Edit', 'obj': tenant,
    })

@staff_required
def tenant_detail(request, pk):
    """Per-tenant overview: users, recent sales, settings snapshot."""
    tenant = get_object_or_404(Tenant, pk=pk)
    today = timezone.now().date()
    this_month = today.replace(day=1)

    users   = User.objects.filter(tenant=tenant).order_by('role', 'username')
    products = Product.objects.filter(tenant=tenant, is_active=True).count()
    low_stock = Product.objects.filter(
        tenant=tenant, is_active=True, is_service=False,
        quantity_in_stock__lte=1
    ).count()

    today_rev = Sale.objects.filter(
        tenant=tenant, created_at__date=today, status='completed'
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    month_rev = Sale.objects.filter(
        tenant=tenant, created_at__date__gte=this_month, status='completed'
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    month_tx = Sale.objects.filter(
        tenant=tenant, created_at__date__gte=this_month, status='completed'
    ).count()

    recent_sales = Sale.objects.filter(tenant=tenant).order_by('-created_at')[:10]
    sys = SystemSetting.get_settings(tenant)

    return render(request, 'platform/tenant_detail.html', {
        'tenant': tenant, 'users': users, 'sys': sys,
        'products': products, 'low_stock': low_stock,
        'today_rev': today_rev, 'month_rev': month_rev, 'month_tx': month_tx,
        'recent_sales': recent_sales,
    })


@staff_required
def tenant_toggle(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    tenant.is_active = not tenant.is_active
    tenant.save()
    state = 'activated' if tenant.is_active else 'deactivated'
    messages.success(request, f'"{tenant.name}" {state}.')
    return redirect('platform:tenant_list')


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
            user.tenant = None
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
