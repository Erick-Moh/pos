"""pos/views.py — Tenant-scoped POS views."""

import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from users.decorators import login_required_tenant
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from inventory.models import Product, StockMovement
from settings_app.models import SystemSetting
from tenants.mixins import get_tenant_or_404
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
        if customer_id:
            try:
                sale.customer = Customer.objects.get(pk=customer_id, tenant=tenant)
            except Customer.DoesNotExist:
                pass
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

            if not product.is_service and product.quantity_in_stock < qty:
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
            if not product.is_service:
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
            if not item.product.is_service:
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
