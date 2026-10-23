"""pos/views.py"""

import json
from decimal import Decimal
from datetime import date as date_type
from django.shortcuts import render, redirect, get_object_or_404
from users.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from django.db.models import F, Sum, Count, Q
from inventory.models import Product, StockMovement
from settings_app.models import SystemSetting
from users.decorators import admin_required, admin_only, admin_or_cashier
from .models import Sale, SaleItem, Customer, CreditRepayment


@login_required
def dashboard(request):
    today = timezone.now().date()
    today_sales = Sale.objects.filter(created_at__date=today, status='completed')
    today_revenue = sum(s.total_amount for s in today_sales)
    recent_sales = Sale.objects.filter(status='completed').select_related('served_by', 'customer')[:10]
    low_stock = Product.objects.filter(
        quantity_in_stock__lte=F('reorder_level'), is_active=True, is_service=False
    )[:5]
    sys = SystemSetting.get_settings()
    return render(request, 'pos/dashboard.html', {
        'today_revenue': today_revenue,
        'today_count': today_sales.count(),
        'recent_sales': recent_sales,
        'low_stock': low_stock,
        'currency': sys.currency_symbol,
        'current_hour': timezone.localtime().hour,
    })


@login_required
def pos_terminal(request):
    products = Product.objects.filter(is_active=True).select_related('category').order_by('category__name', 'name')
    categories = Product.objects.filter(is_active=True, category__isnull=False).values_list('category__id', 'category__name').distinct().order_by('category__name')
    customers = Customer.objects.filter(is_active=True).values('id', 'name', 'phone')
    sys = SystemSetting.get_settings()
    return render(request, 'pos/terminal.html', {
        'products': products, 'categories': categories,
        'customers': list(customers),
        'currency': sys.currency_symbol,
        'vat_rate': float(sys.vat_rate),
    })


@login_required
@require_POST
def process_sale(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    cart_items = data.get('items', [])
    if not cart_items:
        return JsonResponse({'success': False, 'error': 'Cart is empty.'}, status=400)

    cash_method = data.get('payment_method', 'cash')   # method used for the paid-now portion
    amount_tendered = Decimal(str(data.get('amount_tendered', 0)))
    credit_portion  = Decimal(str(data.get('credit_portion', 0)))
    discount_percent = Decimal(str(data.get('discount_percent', 0)))
    discount_amount_manual = Decimal(str(data.get('discount_amount', 0)))
    customer_id = data.get('customer_id')
    credit_due_date_str = data.get('credit_due_date', '')
    credit_due_date = None

    # ── Resolve payment_method for the Sale record ───────────────────────
    # We never use 'split'. The cash-portion method (cash/mpesa/card) is
    # always stored. 'credit' is used only when nothing is paid now.
    if credit_portion > 0 and amount_tendered == 0:
        payment_method = 'credit'
    else:
        payment_method = cash_method

    # ── Customer lookup ──────────────────────────────────────────────────
    customer = None
    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=400)

    # ── Credit portion validation ────────────────────────────────────────
    if credit_portion > 0:
        if not customer:
            return JsonResponse({
                'success': False,
                'error': 'Credit requires a registered customer. Walk-in customers must pay in full.'
            }, status=400)
        if not customer.is_credit_allowed:
            return JsonResponse({
                'success': False,
                'error': f'"{customer.name}" is not authorised for credit. Enable credit in the customer profile first.'
            }, status=400)
        if not credit_due_date_str:
            return JsonResponse({'success': False, 'error': 'A payment due date is required for credit sales.'}, status=400)
        try:
            credit_due_date = date_type.fromisoformat(credit_due_date_str)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid due date format (use YYYY-MM-DD).'}, status=400)
        if credit_due_date < timezone.now().date():
            return JsonResponse({'success': False, 'error': 'Payment due date cannot be in the past.'}, status=400)

    sys = SystemSetting.get_settings()
    vat_rate = sys.vat_rate / 100

    with transaction.atomic():
        sale = Sale(
            served_by=request.user,
            payment_method=payment_method,
            amount_tendered=amount_tendered,
            discount_percent=discount_percent,
            mpesa_transaction_code=data.get('mpesa_code', '') if cash_method == 'mpesa' else '',
        )
        if customer:
            sale.customer = customer

        # Set credit fields when there is a deferred portion
        if credit_portion > 0:
            sale.credit_portion = credit_portion
            sale.credit_due_date = credit_due_date
            sale.credit_paid = False

        sale.save()

        subtotal = Decimal('0')
        for item_data in cart_items:
            try:
                product = Product.objects.select_for_update().get(pk=item_data['product_id'], is_active=True)
            except Product.DoesNotExist:
                sale.delete()
                return JsonResponse({'success': False, 'error': f'Product not found.'}, status=400)

            qty = Decimal(str(item_data.get('quantity', 1)))
            unit_price = Decimal(str(item_data.get('unit_price', product.selling_price)))
            item_discount = Decimal(str(item_data.get('discount', 0)))

            # track_stock = False means no quantity enforcement (e.g. loose food)
            deduct_stock = (not product.is_service) and product.track_stock
            if deduct_stock and product.quantity_in_stock < qty:
                sale.delete()
                return JsonResponse({'success': False, 'error': f'Insufficient stock for "{product.name}".'}, status=400)

            line_total = (unit_price * qty) - item_discount
            subtotal += line_total

            SaleItem.objects.create(
                sale=sale, product=product,
                product_name=product.name, unit_price=unit_price,
                quantity=qty, discount_amount=item_discount, line_total=line_total,
                is_vat_exempt=product.is_vat_exempt,
            )
            if deduct_stock:
                StockMovement.objects.create(
                    product=product,
                    movement_type='sale', quantity=-qty,
                    unit_cost=product.buying_price,
                    reference=sale.invoice_number,
                    performed_by=request.user,
                    quantity_before=product.quantity_in_stock,
                    quantity_after=product.quantity_in_stock - qty,
                )
                product.quantity_in_stock = F('quantity_in_stock') - qty
                product.save()

        if discount_percent > 0:
            sale.discount_amount = subtotal * (discount_percent / 100)
        else:
            sale.discount_amount = discount_amount_manual

        taxable = subtotal - sale.discount_amount
        vat_amount = sum(
            item.line_total * vat_rate for item in sale.items.all() if not item.is_vat_exempt
        )
        sale.subtotal = subtotal
        sale.vat_amount = vat_amount
        sale.total_amount = taxable + vat_amount
        sale.change_given = max(Decimal('0'), amount_tendered - sale.total_amount)
        sale.status = 'completed'

        # ── Credit limit check (against credit_portion only) ────────────
        if credit_portion > 0 and customer and customer.credit_limit > 0:
            current_outstanding = customer.outstanding_balance
            if current_outstanding + credit_portion > customer.credit_limit:
                sale.delete()
                available = max(Decimal('0'), customer.credit_limit - current_outstanding)
                return JsonResponse({
                    'success': False,
                    'error': (
                        f'Credit limit exceeded for "{customer.name}". '
                        f'Limit: {customer.credit_limit:,.2f}, '
                        f'Outstanding: {current_outstanding:,.2f}, '
                        f'Available: {available:,.2f}, '
                        f'Requested credit: {credit_portion:,.2f}.'
                    ),
                }, status=400)

        sale.save()

    # fiscalise_sale_if_enabled(sale)
    return JsonResponse({
        'success': True,
        'invoice_number': sale.invoice_number,
        'total_amount': float(sale.total_amount),
        'change_given': float(sale.change_given),
        'receipt_url': f'/pos/receipt/{sale.pk}/',
    })


@login_required
def credit_check(request):
    """
    GET /pos/api/credit-check/?customer_id=X&amount=Y
    Returns eligibility info for deferring `amount` to credit for customer X.
    Called by the POS terminal JS on every amount-paid change.
    """
    customer_id = request.GET.get('customer_id')
    try:
        amount = Decimal(str(request.GET.get('amount', '0')))
    except Exception:
        return JsonResponse({'eligible': False, 'reason': 'Invalid amount.'}, status=400)

    if not customer_id:
        return JsonResponse({'eligible': False, 'reason': 'No customer selected.'})

    try:
        customer = Customer.objects.get(pk=customer_id, is_active=True)
    except Customer.DoesNotExist:
        return JsonResponse({'eligible': False, 'reason': 'Customer not found.'}, status=404)

    if not customer.is_credit_allowed:
        return JsonResponse({
            'eligible': False,
            'reason': f'"{customer.name}" is not enabled for credit purchases.',
        })

    outstanding = customer.outstanding_balance
    limit = customer.credit_limit
    available = None if limit == 0 else max(Decimal('0'), limit - outstanding)

    if limit > 0 and outstanding + amount > limit:
        return JsonResponse({
            'eligible': False,
            'reason': (
                f'Credit limit exceeded. '
                f'Limit: {limit:,.2f}, '
                f'Outstanding: {outstanding:,.2f}, '
                f'Available: {(available or 0):,.2f}.'
            ),
            'limit': float(limit),
            'outstanding': float(outstanding),
            'available': float(available or 0),
        })

    return JsonResponse({
        'eligible': True,
        'reason': '',
        'limit': float(limit),
        'outstanding': float(outstanding),
        'available': float(available) if available is not None else None,
        'customer_name': customer.name,
    })


@login_required
def receipt_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    sys = SystemSetting.get_settings()
    return render(request, 'pos/receipt.html', {'sale': sale, 'sys': sys})


@login_required
def sale_list(request):
    from datetime import date
    date_from = request.GET.get('from', str(date.today()))
    date_to = request.GET.get('to', str(date.today()))
    payment = request.GET.get('payment', '')
    status = request.GET.get('status', 'completed')

    sales = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).select_related('served_by', 'customer')
    if payment:
        sales = sales.filter(payment_method=payment)
    if status:
        sales = sales.filter(status=status)

    sys = SystemSetting.get_settings()
    return render(request, 'pos/sale_list.html', {
        'sales': sales,
        'total_revenue': sum(s.total_amount for s in sales),
        'date_from': date_from, 'date_to': date_to,
        'payment_filter': payment, 'status_filter': status,
        'currency': sys.currency_symbol,
    })


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, 'pos/sale_detail.html', {'sale': sale})


@login_required
def void_sale(request, pk):
    if not request.user.is_admin_role:
        messages.error(request, 'Only administrators can void sales.')
        return redirect('pos:sale_list')
    sale = Sale.objects.prefetch_related('items').get(pk=pk, status='completed')
    if request.method == 'POST':
        for item in sale.items.all():
            if not item.product.is_service and item.product.track_stock:
                StockMovement.objects.create(
                    product=item.product,
                    movement_type='sale_void', quantity=item.quantity,
                    performed_by=request.user,
                    quantity_before=item.product.quantity_in_stock,
                    quantity_after=item.product.quantity_in_stock + item.quantity,
                )
                item.product.quantity_in_stock = F('quantity_in_stock') + item.quantity
                item.product.save()
        sale.status = 'voided'
        sale.void_reason = request.POST.get('void_reason', '')
        sale.save()
        messages.success(request, f'Sale {sale.invoice_number} voided.')
        return redirect('pos:sale_list')
    return render(request, 'pos/void_confirm.html', {'sale': sale})


# ════════════════════════════════════════════════════════════════════════
#  CUSTOMER MANAGEMENT
# ════════════════════════════════════════════════════════════════════════

@login_required
def customer_list(request):
    """List all customers with outstanding balances highlighted."""
    q = request.GET.get('q', '').strip()
    customers = Customer.objects.filter(is_active=True)
    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    customers = customers.order_by('name')
    sys = SystemSetting.get_settings()
    return render(request, 'pos/customer_list.html', {
        'customers': customers,
        'currency': sys.currency_symbol,
        'q': q,
    })


@login_required
def customer_detail(request, pk):
    """Customer profile page with sales history."""
    customer = get_object_or_404(Customer, pk=pk)
    sys = SystemSetting.get_settings()
    sales = Sale.objects.filter(
        customer=customer, status='completed'
    ).order_by('-created_at')[:50]
    total_spent = Sale.objects.filter(
        customer=customer, status='completed',
        payment_method__in=['cash', 'mpesa', 'card', 'bank']
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    return render(request, 'pos/customer_detail.html', {
        'customer': customer,
        'sales': sales,
        'total_spent': total_spent,
        'currency': sys.currency_symbol,
    })


@login_required
def customer_create(request):
    """Create a new customer."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Customer name is required.')
            return redirect('pos:customer_create')
        try:
            credit_limit_raw = Decimal(request.POST.get('credit_limit', '0') or '0')
        except Exception:
            credit_limit_raw = Decimal('0')
        customer = Customer.objects.create(
            name=name,
            phone=request.POST.get('phone', '').strip() or None,
            email=request.POST.get('email', '').strip() or None,
            kra_pin=request.POST.get('kra_pin', '').strip() or None,
            address=request.POST.get('address', '').strip() or None,
            notes=request.POST.get('notes', '').strip() or None,
            is_credit_allowed='is_credit_allowed' in request.POST,
            credit_limit=credit_limit_raw,
        )
        messages.success(request, f'Customer "{name}" created.')
        return redirect('pos:customer_detail', pk=customer.pk)
    return render(request, 'pos/customer_form.html', {
        'action': 'Create',
    })


@login_required
def customer_edit(request, pk):
    """Edit an existing customer."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Customer name is required.')
            return redirect('pos:customer_edit', pk=pk)
        try:
            credit_limit_raw = Decimal(request.POST.get('credit_limit', '0') or '0')
        except Exception:
            credit_limit_raw = Decimal('0')
        customer.name = name
        customer.phone = request.POST.get('phone', '').strip() or None
        customer.email = request.POST.get('email', '').strip() or None
        customer.kra_pin = request.POST.get('kra_pin', '').strip() or None
        customer.address = request.POST.get('address', '').strip() or None
        customer.notes = request.POST.get('notes', '').strip() or None
        customer.is_credit_allowed = 'is_credit_allowed' in request.POST
        customer.credit_limit = credit_limit_raw
        customer.save()
        messages.success(request, f'Customer "{customer.name}" updated.')
        return redirect('pos:customer_detail', pk=pk)
    return render(request, 'pos/customer_form.html', {
        'action': 'Edit',
        'customer': customer,
    })


@login_required
@admin_required
@require_POST
def customer_delete(request, pk):
    """Soft-delete (deactivate) a customer. Admin only."""
    customer = get_object_or_404(Customer, pk=pk)
    name = customer.name
    customer.is_active = False
    customer.save(update_fields=['is_active'])
    messages.success(request, f'Customer "{name}" deactivated.')
    return redirect('pos:customer_list')


# ════════════════════════════════════════════════════════════════════════
#  CREDIT SALES MANAGEMENT
# ════════════════════════════════════════════════════════════════════════

@login_required
def credit_sales_list(request):
    """List sales that have a credit portion, with partial payment tracking."""
    today = timezone.now().date()
    filter_type = request.GET.get('filter', 'unpaid')

    customer_filter = request.GET.get('customer')
    sales = Sale.objects.filter(
        credit_portion__gt=0, status='completed'
    ).select_related('customer', 'served_by').prefetch_related('repayments').order_by('credit_paid', 'credit_due_date')

    if customer_filter:
        sales = sales.filter(customer_id=customer_filter)
    if filter_type == 'unpaid':
        sales = sales.filter(credit_paid=False)
    elif filter_type == 'overdue':
        sales = sales.filter(credit_paid=False, credit_due_date__lt=today)

    # Total still outstanding = sum of credit_portion minus all repayments
    unpaid = Sale.objects.filter(credit_portion__gt=0, status='completed', credit_paid=False)
    total_credit = unpaid.aggregate(total=Sum('credit_portion'))['total'] or Decimal('0')
    total_repaid_so_far = CreditRepayment.objects.filter(
        sale__in=unpaid
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_outstanding = max(Decimal('0'), total_credit - total_repaid_so_far)
    overdue_count = unpaid.filter(credit_due_date__lt=today).count()

    sys = SystemSetting.get_settings()
    return render(request, 'pos/credit_sales_list.html', {
        'sales': sales,
        'total_outstanding': total_outstanding,
        'overdue_count': overdue_count,
        'today': today,
        'filter_type': filter_type,
        'currency': sys.currency_symbol,
    })


@login_required
def customer_credit_summary(request):
    """Debtor ledger: one row per customer with outstanding credit."""
    today = timezone.now().date()
    unpaid_sales = Sale.objects.filter(
        credit_portion__gt=0, status='completed', credit_paid=False,
        customer__isnull=False
    ).select_related('customer')

    # Group by customer
    from collections import defaultdict
    customer_map = defaultdict(lambda: {
        'customer': None, 'invoices': [], 'total_credit': Decimal('0'),
        'total_repaid': Decimal('0'), 'oldest_due': None, 'overdue': False,
    })

    for sale in unpaid_sales:
        cid = sale.customer_id
        entry = customer_map[cid]
        entry['customer'] = sale.customer
        entry['invoices'].append(sale)
        entry['total_credit'] += sale.credit_portion
        repaid = sale.repayments.aggregate(t=Sum('amount'))['t'] or Decimal('0')
        entry['total_repaid'] += repaid
        if sale.credit_due_date:
            if entry['oldest_due'] is None or sale.credit_due_date < entry['oldest_due']:
                entry['oldest_due'] = sale.credit_due_date
            if sale.credit_due_date < today:
                entry['overdue'] = True

    debtors = []
    for entry in customer_map.values():
        balance = max(Decimal('0'), entry['total_credit'] - entry['total_repaid'])
        if balance > 0:
            debtors.append({
                'customer': entry['customer'],
                'invoices': entry['invoices'],
                'total_credit': entry['total_credit'],
                'total_repaid': entry['total_repaid'],
                'balance': balance,
                'oldest_due': entry['oldest_due'],
                'overdue': entry['overdue'],
            })

    debtors.sort(key=lambda d: (not d['overdue'], d['balance'] * -1))

    total_outstanding = sum(d['balance'] for d in debtors)
    overdue_count = sum(1 for d in debtors if d['overdue'])

    sys = SystemSetting.get_settings()
    return render(request, 'pos/customer_credit_summary.html', {
        'debtors': debtors,
        'total_outstanding': total_outstanding,
        'overdue_count': overdue_count,
        'today': today,
        'currency': sys.currency_symbol,
    })


@login_required
@admin_or_cashier
@require_POST
def record_repayment(request, pk):
    """Record a partial or full repayment against a credit sale."""
    sale = get_object_or_404(Sale, pk=pk, credit_portion__gt=0, status='completed')

    if sale.credit_paid:
        messages.error(request, f'{sale.invoice_number} is already fully settled.')
        return redirect('pos:credit_sales_list')

    try:
        amount = Decimal(str(request.POST.get('amount', '0')))
    except Exception:
        messages.error(request, 'Invalid payment amount.')
        return redirect('pos:credit_sales_list')

    if amount <= Decimal('0'):
        messages.error(request, 'Payment amount must be greater than zero.')
        return redirect('pos:credit_sales_list')

    balance = sale.balance_due
    if amount > balance:
        messages.error(request, f'Amount exceeds balance due ({balance:.2f}). Enter {balance:.2f} or less.')
        return redirect('pos:credit_sales_list')

    payment_method = request.POST.get('payment_method', 'cash')
    reference = request.POST.get('reference', '').strip() or None
    notes = request.POST.get('notes', '').strip() or None

    CreditRepayment.objects.create(
        sale=sale,
        amount=amount,
        payment_method=payment_method,
        reference=reference,
        notes=notes,
        recorded_by=request.user,
    )

    # Mark fully paid if balance is now zero
    if sale.is_fully_paid:
        sale.credit_paid = True
        sale.credit_paid_at = timezone.now()
        sale.credit_paid_by = request.user
        sale.credit_payment_method = payment_method
        sale.save(update_fields=['credit_paid', 'credit_paid_at', 'credit_paid_by', 'credit_payment_method'])
        messages.success(request, f'{sale.invoice_number} fully settled.')
    else:
        remaining = sale.balance_due
        messages.success(request, f'Payment of {amount:.2f} recorded. Balance remaining: {remaining:.2f}.')

    return redirect('pos:credit_sales_list')
