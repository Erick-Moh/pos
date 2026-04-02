"""core/views.py — Public landing page and error handlers."""

from django.shortcuts import render
from tenants.models import Tenant

FEATURES = [
    {
        'icon': 'bi-cart3',
        'color': '#0d6efd',
        'bg': 'rgba(13,110,253,.1)',
        'title': 'Point of Sale',
        'desc': 'Fast, touch-friendly POS terminal. Staff PIN login means quick shift handovers.',
    },
    {
        'icon': 'bi-boxes',
        'color': '#8b5cf6',
        'bg': 'rgba(139,92,246,.1)',
        'title': 'Inventory Management',
        'desc': 'Track stock levels, get low-stock alerts, manage suppliers and categories.',
    },
    {
        'icon': 'bi-phone',
        'color': '#22c55e',
        'bg': 'rgba(34,197,94,.1)',
        'title': 'M-Pesa Integration',
        'desc': 'Accept M-Pesa payments natively. Transaction codes recorded automatically.',
    },
    {
        'icon': 'bi-graph-up-arrow',
        'color': '#f59e0b',
        'bg': 'rgba(245,158,11,.1)',
        'title': 'Finance & Reports',
        'desc': 'Daily close-of-business, monthly and yearly P&L reports with charts.',
    },
    {
        'icon': 'bi-shield-check',
        'color': '#ef4444',
        'bg': 'rgba(239,68,68,.1)',
        'title': 'KRA eTIMS',
        'desc': 'KRA fiscal signatures, QR codes and PIN compliance ',
    },
    {
        'icon': 'bi-people',
        'color': '#0ea5e9',
        'bg': 'rgba(14,165,233,.1)',
        'title': 'Multi-User Access',
        'desc': 'Admins use passwords. Floor staff use fast PINs. Role-based permissions throughout.',
    },
]

STEPS = [
    {
        'title': 'Contact us to register',
        'desc': 'WhatsApp or email us with your business name. We set up your workspace in minutes.',
    },
    {
        'title': 'Receive your access key',
        'desc': 'You get a unique URL like getcore.co.ke/your-business/. Share it only with your team.',
    },
    {
        'title': 'Configure your business settings',
        'desc': 'Add your logo, KRA PIN, M-Pesa details, and brand colours. Takes 5 minutes.',
    },
    {
        'title': 'Add products and staff',
        'desc': 'Import or manually add your inventory. Create staff accounts with PINs.',
    },
    {
        'title': 'Start selling',
        'desc': 'Open the POS terminal and start taking orders. Every transaction is recorded instantly.',
    },
]


def landing_page(request):
    tenant_count = Tenant.objects.filter(is_active=True).count()
    return render(request, 'landing.html', {
        'tenant_count': tenant_count,
        'features': FEATURES,
        'steps': STEPS,
    })


def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    return render(request, 'errors/500.html', status=500)
