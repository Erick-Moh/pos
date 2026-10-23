"""inventory/views.py"""

from django.shortcuts import render, redirect, get_object_or_404
from users.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.db import transaction
from django.http import JsonResponse
from users.decorators import admin_required
from .models import Category, Supplier, Product, StockMovement
from .forms import CategoryForm, SupplierForm, ProductForm, StockAdjustmentForm
from .default_cats import (
    CATEGORY_TREE_BY_BUSINESS
)
from .default_prods import (
    PRODUCTS
)



@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    low_stock_only = request.GET.get('low_stock', '')

    products = Product.objects.select_related('category', 'supplier').filter(
        is_active=True
    )
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query))
    if category_id:
        products = products.filter(Q(category_id=category_id) | Q(category__parent_id=category_id))
    if low_stock_only:
        products = products.filter(quantity_in_stock__lte=F('reorder_level'), is_service=False)

    categories = Category.objects.filter(is_active=True)
    low_stock_count = Product.objects.filter(
        quantity_in_stock__lte=F('reorder_level'), is_active=True, is_service=False
    ).count()

    return render(request, 'inventory/product_list.html', {
        'products': products, 'categories': categories,
        'low_stock_count': low_stock_count, 'query': query,
        'selected_category': category_id, 'low_stock_filter': low_stock_only,
    })


@login_required
@admin_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Product "{product.name}" added.')
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {
        'form': form, 'action': 'Add Product',
    })


@login_required
@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {
        'form': form, 'action': 'Edit Product', 'obj': product,
    })


@login_required
@admin_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    movements = product.movements.all()[:20]
    return render(request, 'inventory/product_detail.html', {
        'product': product, 'movements': movements,
    })

@login_required
@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.movements.exists() or product.sale_items.exists():
        messages.error(request, 'Cannot delete a product that has stock movements or sale items. Consider marking it as inactive instead.')
        return redirect('inventory:product_list')
    product.delete()
    messages.success(request, f'Product "{product.name}" deleted.')
    return redirect('inventory:product_list')

@login_required
@admin_required
def stock_adjustment(request):
    next_url = request.GET.get('next_url', None)
    product_id = request.GET.get('product_id', None)
    if product_id:
        try:
            product = Product.objects.get(pk=product_id)
            initial_data = {
                'product': product
            }
        except Product.DoesNotExist:
            messages.error(request, 'Selected product does not exist.')
            return redirect('inventory:stock_adjustment')
    else:
        initial_data = {}
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            stock_reduction = form.cleaned_data['movement_type'] in ['sale', 'damage', 'transfer']
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            if quantity == 0:
                messages.error(request, 'Quantity cannot be zero.')
                return redirect('inventory:stock_adjustment')
            if product.is_service:
                messages.error(request, 'Cannot adjust stock for a service item.')
                return redirect('inventory:stock_adjustment')
            if stock_reduction:
                if product.quantity_in_stock < quantity:
                    messages.error(request, f'Insufficient stock for "{product.name}". Current stock: {product.quantity_in_stock}.')
                    return redirect('inventory:stock_adjustment')
                else:
                    movement.quantity_before = product.quantity_in_stock
                    product.quantity_in_stock -= quantity
            else:
                movement.quantity_before = product.quantity_in_stock
                product.quantity_in_stock += quantity
            product.save()
            movement.quantity_after = product.quantity_in_stock
            movement.performed_by = request.user
            movement.save()
            messages.success(request, f'Stock adjustment recorded for "{movement.product.name}".')
            if next_url:
                return redirect(next_url)
            return redirect('inventory:product_list')
    else:
        form = StockAdjustmentForm(initial=initial_data)
    return render(request, 'inventory/stock_adjustment.html', {
        'form': form,
    })

@login_required
@admin_required
def stock_adjustment_delete(request, pk):
    movement = get_object_or_404(StockMovement, pk=pk)
    if movement.product.is_service:
        messages.error(request, 'Cannot delete stock movement for a service item.')
        return redirect('inventory:product_detail', pk=movement.product.pk)
    if movement.movement_type in ['purchase', 'return']:
        if movement.product.quantity_in_stock < movement.quantity:
            messages.error(request, f'Cannot delete this movement as it would result in negative stock for "{movement.product.name}". Current stock: {movement.product.quantity_in_stock}.')
            return redirect('inventory:product_detail', pk=movement.product.pk)
    movement.delete()
    messages.success(request, f'Stock adjustment deleted for "{movement.product.name}".')
    return redirect('inventory:product_detail', pk=movement.product.pk)
    
@login_required
@admin_required
def category_list(request):
    categories = Category.objects.all().order_by('parent__name', 'name')
    return render(request, 'inventory/category_list.html', {
        'categories': categories,
    })

@login_required
@admin_required
def load_default_categories(request):
    created_count = 0
    business_type = request.GET.get('type', 'default')

    if business_type == 'bar_and_restaurant':
        # Create a new dict instead of modifying the original
        CATEGORY_TREE = {}
        bar_tree = CATEGORY_TREE_BY_BUSINESS.get('bar', {})
        restaurant_tree = CATEGORY_TREE_BY_BUSINESS.get('restaurant', {})
        CATEGORY_TREE.update(bar_tree)
        CATEGORY_TREE.update(restaurant_tree)
    else:
        CATEGORY_TREE = CATEGORY_TREE_BY_BUSINESS.get(business_type, {})
        if not CATEGORY_TREE:
            CATEGORY_TREE = CATEGORY_TREE_BY_BUSINESS.get('default', {})        
    try:
        with transaction.atomic():
            for parent_name, data in CATEGORY_TREE.items():
                parent_cat, created = Category.objects.get_or_create(
                    name=parent_name,
                    defaults={
                        "description": data.get("desc", ""),
                        "icon": data.get("icon", ""),
                        "parent": None,
                    }
                )
                if created:
                    created_count += 1
                
                # Fixed: children should be a list of tuples
                children = data.get("children", [])
                for child_name, child_desc in children:
                    _, created = Category.objects.get_or_create(
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
        return redirect('inventory:category_list')
    
    return redirect('inventory:category_list')

@login_required
@admin_required
def load_default_products(request):
    created_count = 0
    product_category_names = set(
        Category.objects.filter(parent__isnull=False).values_list('name', flat=True)
    )
    PRODUCT_TREE = [prod for prod in PRODUCTS if prod.get('category') in product_category_names]
    try:
        with transaction.atomic():
            for prod in PRODUCT_TREE:
                # Work with a copy so PRODUCTS list is never mutated
                category_name = prod['category']
                category = Category.objects.filter(name=category_name).first()
                unit = prod.get('unit', 'pcs')
                _, created = Product.objects.get_or_create(
                    name=prod['name'],
                    defaults={
                        'unit': unit,
                        'is_service': prod.get('is_service', False),
                        'category': category,
                    },
                )
                if created:
                    created_count += 1
        messages.success(request, f"{created_count} products loaded successfully.")
    except Exception as e:
        messages.error(request, f"Error loading products: {str(e)}")
    return redirect('inventory:product_list')

@login_required
@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.save()
            messages.success(request, 'Category created.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {
        'form': form, 'action': 'Add Category',
    })

@login_required
@admin_required
def category_edit(request, pk):
    category = get_object_or_404(
        Category,
        pk=pk
    )
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.save()
            messages.success(request, 'Category updated.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'action': 'Edit Category',
    })

@login_required
@admin_required
def category_delete(request, pk):
    category = get_object_or_404(
        Category,
        pk=pk
    )
    if category.subcategories.exists():
        messages.error(request, 'Cannot delete a category that has subcategories.')
        return redirect('inventory:category_list')

    if hasattr(category, 'products') and category.products.exists():
        messages.error(request, 'Cannot delete category in use by products.')
        return redirect('inventory:category_list')
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('inventory:category_list')

@login_required
@admin_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {
        'suppliers': suppliers,
    })


@login_required
@admin_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            sup = form.save(commit=False)
            sup.save()
            messages.success(request, 'Supplier added.')
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {
        'form': form, 'action': 'Add Supplier',
    })


@login_required
@admin_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated.')
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {
        'form': form, 'action': 'Edit Supplier', 'obj': supplier,
    })

@login_required
@admin_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if hasattr(supplier, 'products') and supplier.products.exists():
        messages.error(request, 'Cannot delete supplier in use by products.')
        return redirect('inventory:supplier_list')
    supplier.delete()
    messages.success(request, 'Supplier deleted.')
    return redirect('inventory:supplier_list')
