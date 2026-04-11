# """
# tenants/views.py
# Platform-level views for managing tenants (clients).
# Only accessible to Django superusers via /django-admin/ or dedicated platform views.
# These views are mounted outside the tenant URL namespace.
# """

# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.admin.views.decorators import staff_member_required
# from django.contrib import messages
# from django import forms as dj_forms
# from .models import Tenant
# from .tasks import send_tenant_welcome_email

# class TenantForm(dj_forms.ModelForm):
#     class Meta:
#         model = Tenant
#         fields = ['name', 'slug', 'owner_name', 'owner_email', 'owner_phone',
#                   'plan', 'is_active', 'trial_ends_on']
#         widgets = {
#             'name':          dj_forms.TextInput(attrs={'class': 'form-control'}),
#             'slug':          dj_forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'lowercase-with-hyphens'}),
#             'owner_name':    dj_forms.TextInput(attrs={'class': 'form-control'}),
#             'owner_email':   dj_forms.EmailInput(attrs={'class': 'form-control'}),
#             'owner_phone':   dj_forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254...'}),
#             'plan':          dj_forms.Select(attrs={'class': 'form-select select2'}),
#             'is_active':     dj_forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'trial_ends_on': dj_forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
#         }


# @staff_member_required
# def tenant_list(request):
#     tenants = Tenant.objects.all().order_by('name')
#     return render(request, 'tenants/tenant_list.html', {'tenants': tenants})


# @staff_member_required
# def tenant_create(request):
#     if request.method == 'POST':
#         print('Received tenant creation request with data:', request.POST)
#         form = TenantForm(request.POST)
#         if form.is_valid():
#             tenant = form.save()
#             print(f'Created tenant: {tenant.name} (slug: {tenant.slug})' )
#             send_tenant_welcome_email.delay(
#                 tenant_name=tenant.name,
#                 contact_email=tenant.owner_email,
#                 contact_name=tenant.owner_name,
#             ) 
#             print(f'Sent welcome email task for tenant: {tenant.name} to {tenant.owner_email}')
#             messages.success(request, f'Tenant "{tenant.name}" created. Access key: {tenant.slug}')
#             return redirect('tenants:list')
#         else:
#             print('Tenant creation form errors:', form.errors)
#     else:
#         form = TenantForm()
#     return render(request, 'tenants/tenant_form.html', {'form': form, 'action': 'Create'})


# @staff_member_required
# def tenant_edit(request, pk):
#     tenant = get_object_or_404(Tenant, pk=pk)
#     if request.method == 'POST':
#         form = TenantForm(request.POST, instance=tenant)
#         if form.is_valid():
#             form.save()
#             messages.success(request, f'Tenant "{tenant.name}" updated.')
#             return redirect('tenants:list')
#     else:
#         form = TenantForm(instance=tenant)
#     return render(request, 'tenants/tenant_form.html', {'form': form, 'action': 'Edit', 'obj': tenant})


# @staff_member_required
# def tenant_toggle(request, pk):
#     tenant = get_object_or_404(Tenant, pk=pk)
#     tenant.is_active = not tenant.is_active
#     tenant.save()
#     state = 'activated' if tenant.is_active else 'deactivated'
#     messages.success(request, f'Tenant "{tenant.name}" {state}.')
#     return redirect('tenants:list')

