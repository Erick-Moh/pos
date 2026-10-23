"""finance/views.py"""

from decimal import Decimal
from datetime import date, timedelta
import calendar

from django.shortcuts import render, redirect
from users.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField as DField
from django.utils import timezone

from users.decorators import admin_required
from pos.models import Sale, SaleItem, Customer, CreditRepayment
from inventory.models import Product
from settings_app.models import SystemSetting
from .models import DailySummary, MonthlySummary


def _build_daily_summary(target_date):
    sales = Sale.objects.filter(created_at__date=target_date, status='completed')
    voided = Sale.objects.filter(created_at__date=target_date, status='voided')

    # net_received = the portion of each sale that was actually collected now
    # = total_amount - credit_portion  (for split sales this equals amount_tendered)
    net = ExpressionWrapper(F('total_amount') - F('credit_portion'), output_field=DField(max_digits=14, decimal_places=2))

    agg = sales.aggregate(
        total=Sum('total_amount'),
        vat=Sum('vat_amount'),
        discounts=Sum('discount_amount'),
        # Each method captures only the non-deferred portion for that payment type
        cash=Sum(net, filter=Q(payment_method='cash')),
        mpesa=Sum(net, filter=Q(payment_method='mpesa')),
        card=Sum(net, filter=Q(payment_method='card')),
        # Credit = all deferred portions across every sale (pure credit + split)
        credit=Sum('credit_portion'),
    )
    voided_agg = voided.aggregate(count=Count('id'), amount=Sum('total_amount'))

    cogs = Decimal('0')
    for item in SaleItem.objects.filter(sale__in=sales).select_related('product'):
        cogs += item.quantity * item.product.buying_price

    gross_profit = (agg['total'] or Decimal('0')) - cogs

    summary, _ = DailySummary.objects.get_or_create(date=target_date)
    summary.total_sales        = agg['total']     or Decimal('0')
    summary.total_transactions = sales.count()
    summary.total_vat_collected   = agg['vat']       or Decimal('0')
    summary.total_discounts_given = agg['discounts']  or Decimal('0')
    summary.cash_total   = agg['cash']   or Decimal('0')
    summary.mpesa_total  = agg['mpesa']  or Decimal('0')
    summary.card_total   = agg['card']   or Decimal('0')
    summary.credit_total = agg['credit'] or Decimal('0')

    # Cash actually collected from credit repayments on this day
    repayments_today_qs = CreditRepayment.objects.filter(recorded_at__date=target_date)
    repayments_today = repayments_today_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    summary.credit_repayments_received = repayments_today

    # Cash repayments only (for till count — M-Pesa/card repayments go to other channels)
    cash_repayments_today = repayments_today_qs.filter(
        payment_method='cash'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # expected_cash = cash from cash-method sales + cash received as credit repayments today
    summary.expected_cash = (agg['cash'] or Decimal('0')) + cash_repayments_today
    summary.total_cost_of_goods = cogs
    summary.gross_profit        = gross_profit
    summary.voided_count        = voided_agg['count']  or 0
    summary.voided_amount       = voided_agg['amount'] or Decimal('0')
    return summary


@login_required
@admin_required
def finance_dashboard(request):
    today = timezone.now().date()
    daily = _build_daily_summary(today)

    month_sales = Sale.objects.filter(
        created_at__year=today.year, created_at__month=today.month, status='completed'
    )
    month_revenue = month_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    chart_labels, chart_revenue = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        total = Sale.objects.filter(created_at__date=day, status='completed').aggregate(total=Sum('total_amount'))['total'] or 0
        chart_labels.append(day.strftime('%a %d'))
        chart_revenue.append(float(total))

    cash_received_today = (
        daily.cash_total + daily.mpesa_total + daily.card_total + daily.credit_repayments_received
    )
    sys = SystemSetting.get_settings()
    return render(request, 'finance/dashboard.html', {
        'daily': daily, 'month_revenue': month_revenue, 'month_count': month_sales.count(),
        'chart_labels': chart_labels, 'chart_revenue': chart_revenue,
        'today': today, 'currency': sys.currency_symbol,
        'cash_received_today': cash_received_today,
    })


@login_required
@admin_required
def daily_report(request):
    try:
        target_date = date.fromisoformat(request.GET.get('date', str(timezone.now().date())))
    except ValueError:
        target_date = timezone.now().date()

    # ── Unpaid credit sales due on or before target_date ─────────────────
    unpaid_overdue = Sale.objects.filter(
        credit_portion__gt=0,
        credit_paid=False,
        credit_due_date__lte=target_date,
        status='completed',
    ).select_related('customer').order_by('credit_due_date')

    if request.method == 'POST':
        # Block close if there are overdue unpaid credit sales
        if unpaid_overdue.exists() and not request.POST.get('force_close'):
            messages.error(
                request,
                f'Cannot close day — there are {unpaid_overdue.count()} overdue unpaid credit sale(s). '
                f'Settle them first or confirm force-close below.'
            )
        else:
            summary = _build_daily_summary(target_date)
            actual_cash = request.POST.get('actual_cash')
            if actual_cash:
                summary.actual_cash = Decimal(actual_cash)
                summary.calculate_variance()
            summary.notes = request.POST.get('notes', '')
            summary.is_closed = True
            summary.closed_by = request.user
            summary.save()
            messages.success(request, f'Day {target_date} closed.')
            return redirect('finance:daily_report')

    summary = _build_daily_summary(target_date)
    sales = Sale.objects.filter(created_at__date=target_date, status='completed').select_related('served_by', 'customer')
    top_products = SaleItem.objects.filter(sale__in=sales).values('product_name').annotate(
        total_qty=Sum('quantity'), total_rev=Sum('line_total')
    ).order_by('-total_rev')[:10]

    repayments_today = CreditRepayment.objects.filter(
        recorded_at__date=target_date
    ).select_related('sale__customer', 'recorded_by').order_by('recorded_at')

    total_collected = (
        summary.cash_total + summary.mpesa_total +
        summary.card_total + summary.credit_repayments_received
    )

    # Credit still outstanding at end of day:
    # = credit given in today's sales minus any repayments received today for those same sales
    same_day_repaid = CreditRepayment.objects.filter(
        recorded_at__date=target_date,
        sale__created_at__date=target_date,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net_credit_today = max(Decimal('0'), summary.credit_total - same_day_repaid)

    # Gross profit on collected sales only (exclude still-outstanding credit from revenue)
    collected_revenue = summary.total_sales - net_credit_today
    gross_profit_collected = collected_revenue - summary.total_cost_of_goods

    sys = SystemSetting.get_settings()
    return render(request, 'finance/daily_report.html', {
        'summary': summary, 'sales': sales, 'top_products': top_products,
        'target_date': target_date, 'currency': sys.currency_symbol,
        'unpaid_overdue': unpaid_overdue,
        'total_collected': total_collected,
        'repayments_today': repayments_today,
        'gross_profit_collected': gross_profit_collected,
        'net_credit_today': net_credit_today,
    })


@login_required
@admin_required
def monthly_report(request):
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    month_start = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)

    sales = Sale.objects.filter(created_at__date__gte=month_start, created_at__date__lte=month_end, status='completed')
    net = ExpressionWrapper(F('total_amount') - F('credit_portion'), output_field=DField(max_digits=14, decimal_places=2))
    agg = sales.aggregate(
        total=Sum('total_amount'), vat=Sum('vat_amount'), discounts=Sum('discount_amount'),
        cash=Sum(net, filter=Q(payment_method='cash')),
        mpesa=Sum(net, filter=Q(payment_method='mpesa')),
        card=Sum(net, filter=Q(payment_method='card')),
        credit=Sum('credit_portion'),
    )

    # Outstanding credit = credit extended this month that has not yet been fully repaid
    unpaid_credit_sales = sales.filter(credit_portion__gt=0, credit_paid=False)
    credit_extended = unpaid_credit_sales.aggregate(t=Sum('credit_portion'))['t'] or Decimal('0')
    credit_repaid   = CreditRepayment.objects.filter(sale__in=unpaid_credit_sales).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    credit_outstanding = max(Decimal('0'), credit_extended - credit_repaid)

    daily_data = []
    for d in range(1, last_day + 1):
        rev = Sale.objects.filter(created_at__date=date(year, month, d), status='completed').aggregate(total=Sum('total_amount'))['total'] or 0
        daily_data.append({'day': d, 'revenue': float(rev)})

    top_products = SaleItem.objects.filter(sale__in=sales).values('product_name').annotate(
        qty=Sum('quantity'), revenue=Sum('line_total')
    ).order_by('-revenue')[:10]

    cogs = sum(item.quantity * item.product.buying_price for item in SaleItem.objects.filter(sale__in=sales).select_related('product'))
    sys = SystemSetting.get_settings()

    return render(request, 'finance/monthly_report.html', {
        'year': year, 'month': month, 'month_name': calendar.month_name[month],
        'agg': agg, 'daily_data': daily_data, 'top_products': top_products,
        'cogs': cogs, 'gross_profit': (agg['total'] or Decimal('0')) - cogs,
        'total_transactions': sales.count(),
        'credit_outstanding': credit_outstanding,
        'currency': sys.currency_symbol,
        'years': list(range(today.year - 3, today.year + 1)),
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
    })


@login_required
@admin_required
def yearly_report(request):
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))

    monthly_data, yearly_total, yearly_cogs, yearly_credit_outstanding = [], Decimal('0'), Decimal('0'), Decimal('0')
    for m in range(1, 13):
        sales = Sale.objects.filter(created_at__year=year, created_at__month=m, status='completed')
        rev  = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        cogs = sum(item.quantity * item.product.buying_price for item in SaleItem.objects.filter(sale__in=sales).select_related('product'))

        # Unpaid credit from this month's sales
        unpaid = sales.filter(credit_portion__gt=0, credit_paid=False)
        m_credit_extended = unpaid.aggregate(t=Sum('credit_portion'))['t'] or Decimal('0')
        m_credit_repaid   = CreditRepayment.objects.filter(sale__in=unpaid).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        m_credit_outstanding = max(Decimal('0'), m_credit_extended - m_credit_repaid)

        monthly_data.append({
            'month': calendar.month_abbr[m],
            'revenue': float(rev),
            'cogs': float(cogs),
            'profit': float(rev - cogs),
            'credit_outstanding': float(m_credit_outstanding),
        })
        yearly_total += rev
        yearly_cogs  += cogs
        yearly_credit_outstanding += m_credit_outstanding

    sys = SystemSetting.get_settings()
    return render(request, 'finance/yearly_report.html', {
        'year': year, 'years': list(range(today.year - 3, today.year + 1)),
        'monthly_data': monthly_data, 'yearly_total': yearly_total,
        'yearly_cogs': yearly_cogs, 'yearly_profit': yearly_total - yearly_cogs,
        'yearly_credit_outstanding': yearly_credit_outstanding,
        'currency': sys.currency_symbol,
    })


@login_required
@admin_required
def product_movement_report(request):
    """
    Fast & Slow Movers report.
    Shows products ranked by units sold for a given day / month / year.
    """
    today = timezone.now().date()
    period = request.GET.get('period', 'month')  # day | month | year

    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    day_str = request.GET.get('date', str(today))
    try:
        target_date = date.fromisoformat(day_str)
    except ValueError:
        target_date = today

    # ── Build the sale filter for the chosen period ───────────────────────
    if period == 'day':
        sale_filter = Q(sale__created_at__date=target_date, sale__status='completed')
        period_label = target_date.strftime('%A, %d %B %Y')
    elif period == 'year':
        sale_filter = Q(sale__created_at__year=year, sale__status='completed')
        period_label = str(year)
    else:  # month (default)
        sale_filter = Q(sale__created_at__year=year, sale__created_at__month=month, sale__status='completed')
        period_label = f'{calendar.month_name[month]} {year}'

    # ── Aggregate product-level movement ──────────────────────────────────
    product_movement = (
        SaleItem.objects.filter(sale_filter)
        .values('product_id', 'product_name')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum('line_total'),
            num_transactions=Count('sale', distinct=True),
        )
        .order_by('-total_qty')
    )

    # Separate fast (top half) and slow (bottom half) movers
    movement_list = list(product_movement)
    total_products = len(movement_list)
    split = max(1, total_products // 2)
    fast_movers = movement_list[:split]
    slow_movers = list(reversed(movement_list[split:]))  # slowest first

    sys = SystemSetting.get_settings()
    return render(request, 'finance/product_movement_report.html', {
        'period': period,
        'period_label': period_label,
        'target_date': target_date,
        'year': year,
        'month': month,
        'fast_movers': fast_movers,
        'slow_movers': slow_movers,
        'total_products': total_products,
        'years': list(range(today.year - 3, today.year + 1)),
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'currency': sys.currency_symbol,
    })
