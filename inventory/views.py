"""inventory/views.py — Tenant-scoped inventory views."""

from django.shortcuts import render, redirect, get_object_or_404
from users.decorators import login_required_tenant
from django.contrib import messages
from django.db.models import Q, F
from django.db import transaction
from django.http import JsonResponse
from users.decorators import admin_required
from tenants.mixins import get_tenant_or_404
from .models import Category, Supplier, Product, StockMovement
from .forms import CategoryForm, SupplierForm, ProductForm, StockAdjustmentForm
from .default_cats import (
    CATEGORY_TREE
)



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
            return redirect('tenant:inventory:product_list', tenant_slug=tenant_slug)
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
def product_delete(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    product = get_object_or_404(Product, pk=pk, tenant=tenant)
    if product.movements.exists() or product.sale_items.exists():
        messages.error(request, 'Cannot delete a product that has stock movements or sale items. Consider marking it as inactive instead.')
        return redirect('tenant:inventory:product_list', tenant_slug=tenant_slug)
    product.delete()
    messages.success(request, f'Product "{product.name}" deleted.')
    return redirect('tenant:inventory:product_list', tenant_slug=tenant_slug)

@login_required_tenant
@admin_required
def stock_adjustment(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    next_url = request.GET.get('next_url', None)
    product_id = request.GET.get('product_id', None)
    print(product_id)
    print(next_url)
    if product_id:
        try:
            product = Product.objects.get(pk=product_id, tenant=tenant)
            initial_data = {
                'product': product
            }
            print(f"Initial data for stock adjustment: {initial_data}")
        except Product.DoesNotExist:
            messages.error(request, 'Selected product does not exist.')
            return redirect('tenant:inventory:stock_adjustment', tenant_slug=tenant_slug)
    else:
        initial_data = {}
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST, tenant=tenant)
        movement = form.save(commit=False)
        if form.is_valid():
            stock_reduction = form.cleaned_data['movement_type'] in ['sale', 'damage', 'transfer']
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            if quantity == 0:
                messages.error(request, 'Quantity cannot be zero.')
                return redirect('tenant:inventory:stock_adjustment', tenant_slug=tenant_slug)
            if product.is_service:
                messages.error(request, 'Cannot adjust stock for a service item.')
                return redirect('tenant:inventory:stock_adjustment', tenant_slug=tenant_slug)
            if stock_reduction:
                if product.quantity_in_stock < quantity:
                    messages.error(request, f'Insufficient stock for "{product.name}". Current stock: {product.quantity_in_stock}.')
                    return redirect('tenant:inventory:stock_adjustment', tenant_slug=tenant_slug)
                else:
                    movement.quantity_before = product.quantity_in_stock
                    product.quantity_in_stock -= quantity
            else:
                movement.quantity_before = product.quantity_in_stock
                product.quantity_in_stock += quantity
            product.save()
            movement.quantity_after = product.quantity_in_stock
            movement.tenant = tenant
            movement.performed_by = request.user
            movement.save()
            messages.success(request, f'Stock adjustment recorded for "{movement.product.name}".')
            if next_url:
                return redirect(next_url)
            return redirect('tenant:inventory:product_list', tenant_slug=tenant_slug)
    else:
        form = StockAdjustmentForm(tenant=tenant, initial=initial_data)
    return render(request, 'inventory/stock_adjustment.html', {
        'form': form, 'tenant_slug': tenant_slug,
    })

@login_required_tenant
@admin_required
def stock_adjustment_delete(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    movement = get_object_or_404(StockMovement, pk=pk, tenant=tenant)
    if movement.product.is_service:
        messages.error(request, 'Cannot delete stock movement for a service item.')
        return redirect('tenant:inventory:product_detail', tenant_slug=tenant_slug, pk=movement.product.pk)
    if movement.movement_type in ['purchase', 'return']:
        if movement.product.quantity_in_stock < movement.quantity:
            messages.error(request, f'Cannot delete this movement as it would result in negative stock for "{movement.product.name}". Current stock: {movement.product.quantity_in_stock}.')
            return redirect('tenant:inventory:product_detail', tenant_slug=tenant_slug, pk=movement.product.pk)
    movement.delete()
    messages.success(request, f'Stock adjustment deleted for "{movement.product.name}".')
    return redirect('tenant:inventory:product_detail', tenant_slug=tenant_slug, pk=movement.product.pk)
    
@login_required_tenant
@admin_required
def category_list(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    categories = Category.objects.filter(tenant=tenant).order_by('parent__name', 'name')
    return render(request, 'inventory/category_list.html', {
        'categories': categories, 'tenant_slug': tenant_slug,
    })


@login_required_tenant
@admin_required
def load_default_categories(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    created_count = 0
    try:
        with transaction.atomic():
            for parent_name, data in CATEGORY_TREE.items():
                parent_cat, created = Category.objects.get_or_create(
                    tenant=tenant,
                    name=parent_name,
                    defaults={
                        "description": data.get("desc"),
                        "icon": data.get("icon"),
                        "parent": None,
                    }
                )
                if created:
                    created_count += 1
                for child_name, child_desc in data.get("children", []):
                    _, created = Category.objects.get_or_create(
                        tenant=tenant,
                        name=child_name,
                        defaults={
                            "description": child_desc,
                            "parent": parent_cat,
                        }
                    )
                    if created:
                        created_count += 1
        messages.success(request, f"{created_count} categories loaded successfully.")
    except Exception as e:
        messages.error(request, f"Error loading categories: {str(e)}")
    return redirect('tenant:inventory:category_list', tenant_slug=tenant_slug)

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
            return redirect('tenant:inventory:category_list', tenant_slug=tenant_slug)
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {
        'form': form, 'action': 'Add Category', 'tenant_slug': tenant_slug,
    })

@login_required_tenant
@admin_required
def category_edit(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    category = get_object_or_404(
        Category,
        pk=pk,
        tenant=tenant
    )
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.tenant = tenant
            cat.save()
            messages.success(request, 'Category updated.')
            return redirect('tenant:inventory:category_list', tenant_slug=tenant_slug)
    else:
        form = CategoryForm(instance=category)

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'action': 'Edit Category',
        'tenant_slug': tenant_slug,
    })

@login_required_tenant
@admin_required
def category_delete(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    category = get_object_or_404(
        Category,
        pk=pk,
        tenant=tenant
    )
    if category.subcategories.exists():
        messages.error(request, 'Cannot delete a category that has subcategories.')
        return redirect('tenant:inventory:category_list', tenant_slug=tenant_slug)

    if hasattr(category, 'products') and category.products.exists():
        messages.error(request, 'Cannot delete category in use by products.')
        return redirect('tenant:inventory:category_list', tenant_slug=tenant_slug)
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('tenant:inventory:category_list', tenant_slug=tenant_slug)

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
            return redirect('tenant:inventory:supplier_list', tenant_slug=tenant_slug)
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
            return redirect('tenant:inventory:supplier_list', tenant_slug=tenant_slug)
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {
        'form': form, 'action': 'Edit Supplier', 'obj': supplier, 'tenant_slug': tenant_slug,
    })

@login_required_tenant
@admin_required
def supplier_delete(request, tenant_slug, pk):
    tenant = get_tenant_or_404(request)
    supplier = get_object_or_404(Supplier, pk=pk, tenant=tenant)
    if hasattr(supplier, 'products') and supplier.products.exists():
        messages.error(request, 'Cannot delete supplier in use by products.')
        return redirect('tenant:inventory:supplier_list', tenant_slug=tenant_slug)
    supplier.delete()
    messages.success(request, 'Supplier deleted.')
    return redirect('tenant:inventory:supplier_list', tenant_slug=tenant_slug)
