"""inventory/forms.py"""

from django import forms
import bleach
from .models import Category, Supplier, Product, StockMovement


def _validate_positive(value):
    if value and value < 1:
        raise forms.ValidationError('Value must be positive and greater than zero.')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'No parent (top-level)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-box-seam'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            return bleach.clean(description, tags=[], strip=True)
        return description


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'kra_pin', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'kra_pin': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if address:
            return bleach.clean(address, tags=[], strip=True)
        return address

    def clean_notes(self):
        notes = self.cleaned_data.get('notes')
        if notes:
            return bleach.clean(notes, tags=[], strip=True)
        return notes


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'barcode', 'description', 'image',
            'category', 'supplier', 'unit',
            'buying_price', 'selling_price', 'wholesale_price',
            'quantity_in_stock', 'reorder_level', 'max_stock_level',
            'is_vat_exempt', 'is_active', 'is_service',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto-generated if blank'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'category': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Select category...'}),
            'supplier': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Select supplier...'}),
            'unit': forms.Select(attrs={'class': 'form-select select2'}),
            'buying_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'wholesale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'max_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'is_vat_exempt': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_service': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            return bleach.clean(description, tags=[], strip=True)
        return description
        
    def __init__(self, *args, **kwargs):
        tenant=kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        self.fields['buying_price'].validators.append(_validate_positive)
        self.fields['selling_price'].validators.append(_validate_positive)
        self.fields['wholesale_price'].validators.append(_validate_positive)
        self.fields['quantity_in_stock'].validators.append(_validate_positive)
        self.fields['reorder_level'].validators.append(_validate_positive)
        self.fields['max_stock_level'].validators.append(_validate_positive)
        if tenant:
            self.fields['category'].queryset = Category.objects.filter(tenant=tenant, is_active=True)
            self.fields['supplier'].queryset = Supplier.objects.filter(tenant=tenant, is_active=True)
        else:
            self.fields['category'].queryset = Category.objects.none()
            self.fields['supplier'].queryset = Supplier.objects.none()
        
    def save(self, commit=True):
        product = super().save(commit=False)
        # Auto-generate SKU if not provided
        if not product.sku:
            import uuid
            product.sku = f'SKU-{str(uuid.uuid4()).upper()[:8]}'
        if commit:
            product.save()
        return product


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'unit_cost', 'notes', 'reference']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Search product...'}),
            'movement_type': forms.Select(attrs={'class': 'form-select select2'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice / PO number'}),
        }

    def __init__(self, *args, **kwargs):
        tenant=kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        self.fields['quantity'].validators.append(_validate_positive)
        self.fields['unit_cost'].validators.append(_validate_positive)
        if tenant:
            self.fields['product'].queryset = Product.objects.filter(tenant=tenant, is_active=True)
        else:
            self.fields['product'].queryset = Product.objects.none()

    def clean_notes(self):
        notes = self.cleaned_data.get('notes')
        if notes:
            return bleach.clean(notes, tags=[], strip=True)
        return notes
