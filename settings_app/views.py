"""settings_app/views.py — Tenant-scoped settings."""

from django.shortcuts import render, redirect
from users.decorators import login_required_tenant
from django.contrib import messages
from users.decorators import admin_required
from tenants.mixins import get_tenant_or_404
from .models import SystemSetting
from .forms import SystemSettingForm


@login_required_tenant
@admin_required
def settings_dashboard(request, tenant_slug):
    tenant = get_tenant_or_404(request)
    settings_obj = SystemSetting.get_settings(tenant)

    if request.method == 'POST':
        form = SystemSettingForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            s = form.save(commit=False)
            s.tenant = tenant
            s.save()
            messages.success(request, 'Settings updated.')
            return redirect('tenant:settings_app:dashboard', tenant_slug=tenant_slug)
        else:
            messages.error(request, form.errors.as_text())
    else:
        form = SystemSettingForm(instance=settings_obj)

    return render(request, 'settings_app/dashboard.html', {
        'form': form, 'settings_obj': settings_obj, 'tenant_slug': tenant_slug,
    })
