"""inventory/views.py — Tenant-scoped inventory views."""

from django.shortcuts import render, redirect, get_object_or_404
from users.decorators import login_required_tenant
from django.contrib import messages
from django.db.models import Q, F
from django.http import JsonResponse
from users.decorators import admin_required
from tenants.mixins import get_tenant_or_404
from .models import Category, Supplier, Product, StockMovement
from .forms import CategoryForm, SupplierForm, ProductForm, StockAdjustmentForm


@login_required_tenant
def product_list(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    low_stock_only = request.GET.get('low_stock', '')

    products = Product.objects.select_related('category', 'supplier').filter(
        tenant=tenant, is_active=True
    )
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    if low_stock_only:
        products = products.filter(quantity_in_stock__lte=F('reorder_level'), is_service=False)

    categories = Category.objects.filter(tenant=tenant, is_active=True)
    low_stock_count = Product.objects.filter(
        tenant=tenant, quantity_in_stock__lte=F('reorder_level'), is_active=True, is_service=False
    ).count()

    return render(request, 'inventory/product_list.html', {
        'products': products, 'categories': categories,
        'low_stock_count': low_stock_count, 'query': query,
        'selected_category': category_id, 'low_stock_filter': low_stock_only,
        'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def product_create(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, tenant=tenant)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant = tenant
            product.created_by = request.user
            product.save()
            messages.success(request, f'Product "{product.name}" added.')
            return redirect('inventory:product_list', tenant_slug=tenant_slug)
    else:
        form = ProductForm(tenant=tenant)
    return render(request, 'inventory/product_form.html', {
        'form': form, 'action': 'Add Product', 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def product_edit(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    product = get_object_or_404(Product, pk=pk, tenant=tenant)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, tenant=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('tenant:inventory:product_list', tenant_slug=tenant_slug)
    else:
        form = ProductForm(instance=product, tenant=tenant)
    return render(request, 'inventory/product_form.html', {
        'form': form, 'action': 'Edit Product', 'obj': product, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def product_detail(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    product = get_object_or_404(Product, pk=pk, tenant=tenant)
    movements = product.movements.all()[:20]
    return render(request, 'inventory/product_detail.html', {
        'product': product, 'movements': movements, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def stock_adjustment(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.tenant = tenant
            movement.performed_by = request.user
            movement.save()
            messages.success(request, f'Stock adjustment recorded for "{movement.product.name}".')
            return redirect('inventory:product_list', tenant_slug=tenant_slug)
    else:
        form = StockAdjustmentForm()
    return render(request, 'inventory/stock_adjustment.html', {
        'form': form, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def category_list(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    categories = Category.objects.filter(tenant=tenant)
    return render(request, 'inventory/category_list.html', {
        'categories': categories, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def category_create(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.tenant = tenant
            cat.save()
            messages.success(request, 'Category created.')
            return redirect('inventory:category_list', tenant_slug=tenant_slug)
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {
        'form': form, 'action': 'Add Category', 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def supplier_list(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    suppliers = Supplier.objects.filter(tenant=tenant)
    return render(request, 'inventory/supplier_list.html', {
        'suppliers': suppliers, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def supplier_create(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            sup = form.save(commit=False)
            sup.tenant = tenant
            sup.save()
            messages.success(request, 'Supplier added.')
            return redirect('inventory:supplier_list', tenant_slug=tenant_slug)
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {
        'form': form, 'action': 'Add Supplier', 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def supplier_edit(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    supplier = get_object_or_404(Supplier, pk=pk, tenant=tenant)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated.')
            return redirect('inventory:supplier_list', tenant_slug=tenant_slug)
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {
        'form': form, 'action': 'Edit Supplier', 'obj': supplier, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
def product_search_api(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        tenant=tenant, is_active=True, name__icontains=query
    ).values('id', 'name', 'sku', 'selling_price', 'quantity_in_stock', 'unit', 'is_service')[:20]
    return JsonResponse({'products': list(products)})
