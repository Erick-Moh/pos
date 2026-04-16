"""pos/views.py — Tenant-scoped POS views."""

import json
from decimal import Decimal
from datetime import date as date_type
from django.shortcuts import render, redirect, get_object_or_404
from users.decorators import login_required_tenant
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from django.db.models import F, Sum, Count, Q
from inventory.models import Product, StockMovement
from settings_app.models import SystemSetting
from tenants.mixins import get_tenant_or_404
from users.decorators import admin_required
from .models import Sale, SaleItem, Customer


@login_required_tenant
def dashboard(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    today = timezone.now().date()
    today_sales = Sale.objects.filter(tenant=tenant, created_at__date=today, status='completed')
    today_revenue = sum(s.total_amount for s in today_sales)
    recent_sales = Sale.objects.filter(tenant=tenant, status='completed').select_related('served_by', 'customer')[:10]
    low_stock = Product.objects.filter(
        tenant=tenant, quantity_in_stock__lte=F('reorder_level'), is_active=True, is_service=False
    )[:5]
    sys = SystemSetting.get_settings(tenant)
    return render(request, 'pos/dashboard.html', {
        'today_revenue': today_revenue,
        'today_count': today_sales.count(),
        'recent_sales': recent_sales,
        'low_stock': low_stock,
        'currency': sys.currency_symbol,
        'tenant_slug': tenant_slug,
        'current_hour': timezone.localtime().hour,
    })


@login_required_tenant
def pos_terminal(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    products = Product.objects.filter(tenant=tenant, is_active=True).select_related('category').order_by('category__name', 'name')
    categories = products.values_list('category__id', 'category__name').distinct()
    customers = Customer.objects.filter(tenant=tenant, is_active=True).values('id', 'name', 'phone')
    sys = SystemSetting.get_settings(tenant)
    return render(request, 'pos/terminal.html', {
        'products': products, 'categories': categories,
        'customers': list(customers),
        'currency': sys.currency_symbol,
        'vat_rate': float(sys.vat_rate),
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
@require_POST
def process_sale(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    cart_items = data.get('items', [])
    if not cart_items:
        return JsonResponse({'success': False, 'error': 'Cart is empty.'}, status=400)

    payment_method = data.get('payment_method', 'cash')
    amount_tendered = Decimal(str(data.get('amount_tendered', 0)))
    discount_percent = Decimal(str(data.get('discount_percent', 0)))
    discount_amount_manual = Decimal(str(data.get('discount_amount', 0)))
    customer_id = data.get('customer_id')
    credit_due_date_str = data.get('credit_due_date', '')

    # ── Credit Validation ────────────────────────────────────────────────
    customer = None
    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id, tenant=tenant)
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=400)

    if payment_method == 'credit':
        if not customer:
            return JsonResponse({
                'success': False,
                'error': 'Credit sales require a registered customer. Walk-in customers must pay immediately.'
            }, status=400)
        if not customer.is_credit_allowed:
            return JsonResponse({
                'success': False,
                'error': f'Customer "{customer.name}" is not authorised for credit purchases. Enable credit in the customer profile first.'
            }, status=400)
        if not credit_due_date_str:
            return JsonResponse({'success': False, 'error': 'A credit due date is required for credit sales.'}, status=400)
        try:
            credit_due_date = date_type.fromisoformat(credit_due_date_str)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid credit due date format (use YYYY-MM-DD).'}, status=400)
        if credit_due_date < timezone.now().date():
            return JsonResponse({'success': False, 'error': 'Credit due date cannot be in the past.'}, status=400)

    sys = SystemSetting.get_settings(tenant)
    vat_rate = sys.vat_rate / 100

    with transaction.atomic():
        sale = Sale(
            tenant=tenant,
            served_by=request.user,
            payment_method=payment_method,
            amount_tendered=amount_tendered,
            discount_percent=discount_percent,
            mpesa_transaction_code=data.get('mpesa_code', '') if payment_method == 'mpesa' else '',
        )
        if customer:
            sale.customer = customer

        # Set credit fields
        if payment_method == 'credit':
            sale.credit_due_date = credit_due_date
            sale.credit_paid = False
            sale.amount_tendered = Decimal('0')  # Nothing tendered yet

        sale.save()

        subtotal = Decimal('0')
        for item_data in cart_items:
            try:
                product = Product.objects.select_for_update().get(pk=item_data['product_id'], tenant=tenant, is_active=True)
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
                    tenant=tenant, product=product,
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
        sale.save()

    # fiscalise_sale_if_enabled(sale)
    return JsonResponse({
        'success': True,
        'invoice_number': sale.invoice_number,
        'total_amount': float(sale.total_amount),
        'change_given': float(sale.change_given),
        'receipt_url': f'/{tenant_slug}/pos/receipt/{sale.pk}/',
    })


@login_required_tenant
def receipt_view(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    sale = get_object_or_404(Sale, pk=pk, tenant=tenant)
    sys = SystemSetting.get_settings(tenant)
    return render(request, 'pos/receipt.html', {'sale': sale, 'sys': sys, 'tenant_slug': tenant_slug})


@login_required_tenant
def sale_list(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    from datetime import date
    date_from = request.GET.get('from', str(date.today()))
    date_to = request.GET.get('to', str(date.today()))
    payment = request.GET.get('payment', '')
    status = request.GET.get('status', 'completed')

    sales = Sale.objects.filter(
        tenant=tenant,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).select_related('served_by', 'customer')
    if payment:
        sales = sales.filter(payment_method=payment)
    if status:
        sales = sales.filter(status=status)

    sys = SystemSetting.get_settings(tenant)
    return render(request, 'pos/sale_list.html', {
        'sales': sales,
        'total_revenue': sum(s.total_amount for s in sales),
        'date_from': date_from, 'date_to': date_to,
        'payment_filter': payment, 'status_filter': status,
        'currency': sys.currency_symbol,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
def sale_detail(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    sale = get_object_or_404(Sale, pk=pk, tenant=tenant)
    return render(request, 'pos/sale_detail.html', {'sale': sale, 'tenant_slug': tenant_slug})


@login_required_tenant
def void_sale(request, tenant_slug, pk):
    if not request.user.is_admin_role:
        messages.error(request, 'Only administrators can void sales.')
        return redirect('tenant:pos:sale_list', tenant_slug=tenant_slug)
    tenant = get_tenant_or_404(request)
    sale = Sale.objects.prefetch_related('items').get(pk=pk, tenant=tenant, status='completed')
    if request.method == 'POST':
        for item in sale.items.all():
            if not item.product.is_service and item.product.track_stock:
                StockMovement.objects.create(
                    tenant=tenant, product=item.product,
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
        return redirect('tenant:pos:sale_list', tenant_slug=tenant_slug)
    return render(request, 'pos/void_confirm.html', {'sale': sale, 'tenant_slug': tenant_slug})


# ════════════════════════════════════════════════════════════════════════
#  CUSTOMER MANAGEMENT
# ════════════════════════════════════════════════════════════════════════

@login_required_tenant
def customer_list(request, tenant_slug):
    """List all customers with outstanding balances highlighted."""
    tenant = get_tenant_or_404(request)
    q = request.GET.get('q', '').strip()
    customers = Customer.objects.filter(tenant=tenant, is_active=True)
    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    customers = customers.order_by('name')
    sys = SystemSetting.get_settings(tenant)
    return render(request, 'pos/customer_list.html', {
        'customers': customers,
        'currency': sys.currency_symbol,
        'tenant_slug': tenant_slug,
        'q': q,
    })


@login_required_tenant
def customer_detail(request, tenant_slug, pk):
    """Customer profile page with sales history."""
    tenant = get_tenant_or_404(request)
    customer = get_object_or_404(Customer, pk=pk, tenant=tenant)
    sys = SystemSetting.get_settings(tenant)
    sales = Sale.objects.filter(
        tenant=tenant, customer=customer, status='completed'
    ).order_by('-created_at')[:50]
    total_spent = Sale.objects.filter(
        tenant=tenant, customer=customer, status='completed',
        payment_method__in=['cash', 'mpesa', 'card', 'bank']
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    return render(request, 'pos/customer_detail.html', {
        'customer': customer,
        'sales': sales,
        'total_spent': total_spent,
        'currency': sys.currency_symbol,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
def customer_create(request, tenant_slug):
    """Create a new customer. Any tenant user can do this."""
    tenant = get_tenant_or_404(request)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Customer name is required.')
            return redirect('tenant:pos:customer_create', tenant_slug=tenant_slug)
        try:
            credit_limit_raw = Decimal(request.POST.get('credit_limit', '0') or '0')
        except Exception:
            credit_limit_raw = Decimal('0')
        customer = Customer.objects.create(
            tenant=tenant,
            name=name,
            phone=request.POST.get('phone', '').strip() or None,
            email=request.POST.get('email', '').strip() or None,
            kra_pin=request.POST.get('kra_pin', '').strip() or None,
            address=request.POST.get('address', '').strip() or None,
            notes=request.POST.get('notes', '').strip() or None,
            is_credit_allowed='is_credit_allowed' in request.POST,
            credit_limit=credit_limit_raw,
        )
        messages.success(request, f'Customer "{name}" created successfully.')
        return redirect('tenant:pos:customer_detail', tenant_slug=tenant_slug, pk=customer.pk)
    return render(request, 'pos/customer_form.html', {
        'action': 'Create',
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
def customer_edit(request, tenant_slug, pk):
    """Edit an existing customer. Any tenant user can do this."""
    tenant = get_tenant_or_404(request)
    customer = get_object_or_404(Customer, pk=pk, tenant=tenant)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Customer name is required.')
            return redirect('tenant:pos:customer_edit', tenant_slug=tenant_slug, pk=pk)
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
        return redirect('tenant:pos:customer_detail', tenant_slug=tenant_slug, pk=pk)
    return render(request, 'pos/customer_form.html', {
        'action': 'Edit',
        'customer': customer,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
@require_POST
def customer_delete(request, tenant_slug, pk):
    """Soft-delete (deactivate) a customer. Admin only."""
    tenant = get_tenant_or_404(request)
    customer = get_object_or_404(Customer, pk=pk, tenant=tenant)
    name = customer.name
    customer.is_active = False
    customer.save(update_fields=['is_active'])
    messages.success(request, f'Customer "{name}" has been deactivated.')
    return redirect('tenant:pos:customer_list', tenant_slug=tenant_slug)


# ════════════════════════════════════════════════════════════════════════
#  CREDIT SALES MANAGEMENT
# ════════════════════════════════════════════════════════════════════════

@login_required_tenant
@admin_required
def credit_sales_list(request, tenant_slug):
    """
    List all unpaid credit sales.
    Overdue ones (due_date < today) are flagged in red.
    """
    tenant = get_tenant_or_404(request)
    today = timezone.now().date()

    filter_type = request.GET.get('filter', 'unpaid')  # unpaid | overdue | all
    sales = Sale.objects.filter(
        tenant=tenant, payment_method='credit', status='completed'
    ).select_related('customer', 'served_by').order_by('credit_paid', 'credit_due_date')

    if filter_type == 'unpaid':
        sales = sales.filter(credit_paid=False)
    elif filter_type == 'overdue':
        sales = sales.filter(credit_paid=False, credit_due_date__lt=today)
    # 'all' → no extra filter

    total_outstanding = sales.filter(credit_paid=False).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    overdue_count = sales.filter(credit_paid=False, credit_due_date__lt=today).count()

    sys = SystemSetting.get_settings(tenant)
    return render(request, 'pos/credit_sales_list.html', {
        'sales': sales,
        'total_outstanding': total_outstanding,
        'overdue_count': overdue_count,
        'today': today,
        'filter_type': filter_type,
        'currency': sys.currency_symbol,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
@require_POST
def mark_credit_paid(request, tenant_slug, pk):
    """
    Mark a credit sale as settled.
    Accepts payment method + optional reference (e.g. M-Pesa code).
    """
    tenant = get_tenant_or_404(request)
    sale = get_object_or_404(Sale, pk=pk, tenant=tenant, payment_method='credit', credit_paid=False)

    payment_method = request.POST.get('payment_method', 'cash')
    reference = request.POST.get('reference', '').strip()

    sale.credit_paid = True
    sale.credit_paid_at = timezone.now()
    sale.credit_paid_by = request.user
    sale.credit_payment_method = payment_method
    sale.credit_payment_reference = reference or None
    sale.save()

    messages.success(
        request,
        f'Credit sale {sale.invoice_number} marked as paid '
        f'({"" if not reference else reference + " — "}{sale.get_credit_payment_method_display()}).'
    )
    return redirect('tenant:pos:credit_sales_list', tenant_slug=tenant_slug)
