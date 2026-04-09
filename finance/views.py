"""finance/views.py — Tenant-scoped finance views."""

from decimal import Decimal
from datetime import date, timedelta
import calendar

from django.shortcuts import render, redirect
from users.decorators import login_required_tenant
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone

from users.decorators import admin_required
from tenants.mixins import get_tenant_or_404
from pos.models import Sale, SaleItem
from inventory.models import Product
from settings_app.models import SystemSetting
from .models import DailySummary, MonthlySummary


def _build_daily_summary(tenant, target_date):
    sales = Sale.objects.filter(tenant=tenant, created_at__date=target_date, status='completed')
    voided = Sale.objects.filter(tenant=tenant, created_at__date=target_date, status='voided')

    agg = sales.aggregate(
        total=Sum('total_amount'), vat=Sum('vat_amount'), discounts=Sum('discount_amount'),
        cash=Sum('total_amount', filter=Q(payment_method='cash')),
        mpesa=Sum('total_amount', filter=Q(payment_method='mpesa')),
        card=Sum('total_amount', filter=Q(payment_method='card')),
        credit=Sum('total_amount', filter=Q(payment_method='credit')),
    )
    voided_agg = voided.aggregate(count=Count('id'), amount=Sum('total_amount'))

    cogs = Decimal('0')
    for item in SaleItem.objects.filter(sale__in=sales).select_related('product'):
        cogs += item.quantity * item.product.buying_price

    gross_profit = (agg['total'] or Decimal('0')) - cogs

    summary, _ = DailySummary.objects.get_or_create(tenant=tenant, date=target_date)
    summary.total_sales = agg['total'] or Decimal('0')
    summary.total_transactions = sales.count()
    summary.total_vat_collected = agg['vat'] or Decimal('0')
    summary.total_discounts_given = agg['discounts'] or Decimal('0')
    summary.cash_total = agg['cash'] or Decimal('0')
    summary.mpesa_total = agg['mpesa'] or Decimal('0')
    summary.card_total = agg['card'] or Decimal('0')
    summary.credit_total = agg['credit'] or Decimal('0')
    summary.expected_cash = agg['cash'] or Decimal('0')
    summary.total_cost_of_goods = cogs
    summary.gross_profit = gross_profit
    summary.voided_count = voided_agg['count'] or 0
    summary.voided_amount = voided_agg['amount'] or Decimal('0')
    return summary


@login_required_tenant
@admin_required
def finance_dashboard(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    today = timezone.now().date()
    daily = _build_daily_summary(tenant, today)

    month_sales = Sale.objects.filter(
        tenant=tenant, created_at__year=today.year, created_at__month=today.month, status='completed'
    )
    month_revenue = month_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    chart_labels, chart_revenue = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        total = Sale.objects.filter(tenant=tenant, created_at__date=day, status='completed').aggregate(total=Sum('total_amount'))['total'] or 0
        chart_labels.append(day.strftime('%a %d'))
        chart_revenue.append(float(total))

    sys = SystemSetting.get_settings(tenant)
    return render(request, 'finance/dashboard.html', {
        'daily': daily, 'month_revenue': month_revenue, 'month_count': month_sales.count(),
        'chart_labels': chart_labels, 'chart_revenue': chart_revenue,
        'today': today, 'currency': sys.currency_symbol, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def daily_report(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    try:
        target_date = date.fromisoformat(request.GET.get('date', str(timezone.now().date())))
    except ValueError:
        target_date = timezone.now().date()

    if request.method == 'POST':
        summary = _build_daily_summary(tenant, target_date)
        actual_cash = request.POST.get('actual_cash')
        if actual_cash:
            summary.actual_cash = Decimal(actual_cash)
            summary.calculate_variance()
        summary.notes = request.POST.get('notes', '')
        summary.is_closed = True
        summary.closed_by = request.user
        summary.save()
        messages.success(request, f'Day {target_date} closed.')
        return redirect('tenant:finance:daily_report', tenant_slug=tenant_slug)

    summary = _build_daily_summary(tenant, target_date)
    sales = Sale.objects.filter(tenant=tenant, created_at__date=target_date, status='completed').select_related('served_by', 'customer')
    top_products = SaleItem.objects.filter(sale__in=sales).values('product_name').annotate(
        total_qty=Sum('quantity'), total_rev=Sum('line_total')
    ).order_by('-total_rev')[:10]

    sys = SystemSetting.get_settings(tenant)
    return render(request, 'finance/daily_report.html', {
        'summary': summary, 'sales': sales, 'top_products': top_products,
        'target_date': target_date, 'currency': sys.currency_symbol, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def monthly_report(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    month_start = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    sales = Sale.objects.filter(tenant=tenant, created_at__date__gte=month_start, created_at__date__lte=month_end, status='completed')
    agg = sales.aggregate(
        total=Sum('total_amount'), vat=Sum('vat_amount'), discounts=Sum('discount_amount'),
        cash=Sum('total_amount', filter=Q(payment_method='cash')),
        mpesa=Sum('total_amount', filter=Q(payment_method='mpesa')),
        card=Sum('total_amount', filter=Q(payment_method='card')),
    )
    daily_data = []
    for d in range(1, last_day + 1):
        rev = Sale.objects.filter(tenant=tenant, created_at__date=date(year, month, d), status='completed').aggregate(total=Sum('total_amount'))['total'] or 0
        daily_data.append({'day': d, 'revenue': float(rev)})

    top_products = SaleItem.objects.filter(sale__in=sales).values('product_name').annotate(
        qty=Sum('quantity'), revenue=Sum('line_total')
    ).order_by('-revenue')[:10]

    cogs = sum(item.quantity * item.product.buying_price for item in SaleItem.objects.filter(sale__in=sales).select_related('product'))
    sys = SystemSetting.get_settings(tenant)

    return render(request, 'finance/monthly_report.html', {
        'year': year, 'month': month, 'month_name': calendar.month_name[month],
        'agg': agg, 'daily_data': daily_data, 'top_products': top_products,
        'cogs': cogs, 'gross_profit': (agg['total'] or Decimal('0')) - cogs,
        'total_transactions': sales.count(),
        'currency': sys.currency_symbol, 'tenant_slug': tenant_slug,
        'years': list(range(today.year - 3, today.year + 1)),
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
    })


@login_required_tenant
@admin_required
def yearly_report(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))

    monthly_data, yearly_total, yearly_cogs = [], Decimal('0'), Decimal('0')
    for m in range(1, 13):
        sales = Sale.objects.filter(tenant=tenant, created_at__year=year, created_at__month=m, status='completed')
        rev = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        cogs = sum(item.quantity * item.product.buying_price for item in SaleItem.objects.filter(sale__in=sales).select_related('product'))
        monthly_data.append({'month': calendar.month_abbr[m], 'revenue': float(rev), 'cogs': float(cogs), 'profit': float(rev - cogs)})
        yearly_total += rev
        yearly_cogs += cogs

    sys = SystemSetting.get_settings(tenant)
    return render(request, 'finance/yearly_report.html', {
        'year': year, 'years': list(range(today.year - 3, today.year + 1)),
        'monthly_data': monthly_data, 'yearly_total': yearly_total,
        'yearly_cogs': yearly_cogs, 'yearly_profit': yearly_total - yearly_cogs,
        'currency': sys.currency_symbol, 'tenant_slug': tenant_slug,
    })
