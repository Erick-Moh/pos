"""
pos/print_api.py
REST API consumed exclusively by the GetCore Print Agent.

All endpoints authenticate via the device token (passed as ?token=<TOKEN> or
X-Device-Token header). No session/cookie auth — the agent runs headlessly.

Endpoints
─────────
POST /api/print/heartbeat/          Agent announces it's alive + printer status
GET  /api/print/jobs/               Agent polls for pending jobs
POST /api/print/jobs/<id>/ack/      Agent marks a job as "sent to printer"
POST /api/print/jobs/<id>/done/     Agent marks a job as "printed successfully"
POST /api/print/jobs/<id>/fail/     Agent marks a job as "failed"
GET  /api/print/status/             Django UI uses this to check if device is ready
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import PrintDevice, PrintJob


# ─── Auth helper ─────────────────────────────────────────────────────────────

def _get_device(request):
    """
    Extract and validate the device token from:
      1. ?token=<TOKEN> query param
      2. X-Device-Token request header
    Returns (PrintDevice | None, error_response | None)
    """
    token = (
        request.GET.get('token')
        or request.POST.get('token')
        or request.headers.get('X-Device-Token', '')
    ).strip()

    if not token:
        return None, JsonResponse({'error': 'Missing device token.'}, status=401)

    try:
        device = PrintDevice.objects.select_related('tenant').get(
            token=token, is_active=True
        )
    except PrintDevice.DoesNotExist:
        return None, JsonResponse({'error': 'Invalid or inactive device token.'}, status=403)

    return device, None


# ─── Heartbeat ───────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def heartbeat(request):
    """
    Called by the agent every ~30 seconds.
    Updates last_seen, printer_name, os_info, agent_version.
    """
    device, err = _get_device(request)
    if err:
        return err

    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    device.last_seen = timezone.now()
    device.is_online = True
    device.printer_name = body.get('printer_name') or device.printer_name
    device.os_info = body.get('os_info') or device.os_info
    device.agent_version = body.get('agent_version') or device.agent_version
    device.save(update_fields=['last_seen', 'is_online', 'printer_name', 'os_info', 'agent_version'])

    # Return any pending jobs count so agent knows to poll immediately
    pending_count = PrintJob.objects.filter(device=device, status='pending').count()

    return JsonResponse({
        'ok': True,
        'device_name': device.name,
        'pending_jobs': pending_count,
        'server_time': timezone.now().isoformat(),
    })


# ─── Poll for jobs ───────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
def poll_jobs(request):
    """
    Agent calls this every 2 seconds. Returns a list of pending print jobs.
    Jobs are returned in order (oldest first — FIFO).
    """
    device, err = _get_device(request)
    if err:
        return err

    # Auto-update heartbeat on poll too (agent poll IS the heartbeat if frequent)
    device.last_seen = timezone.now()
    device.is_online = True
    device.save(update_fields=['last_seen', 'is_online'])

    jobs = PrintJob.objects.filter(
        device=device, status='pending'
    ).order_by('created_at')[:10]  # Max 10 jobs per poll

    jobs_data = []
    for job in jobs:
        jobs_data.append({
            'id': job.pk,
            'receipt_text': job.receipt_text,
            'copies': job.copies,
            'sale_id': job.sale_id,
            'created_at': job.created_at.isoformat(),
        })

    return JsonResponse({
        'ok': True,
        'printer_name': device.printer_name,
        'jobs': jobs_data,
    })


# ─── Job status updates ──────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def job_ack(request, job_id):
    """Agent picked up the job and is sending it to the printer."""
    device, err = _get_device(request)
    if err:
        return err

    try:
        job = PrintJob.objects.get(pk=job_id, device=device, status='pending')
    except PrintJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found or already processed.'}, status=404)

    job.status = 'sent'
    job.sent_at = timezone.now()
    job.save(update_fields=['status', 'sent_at'])
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['POST'])
def job_done(request, job_id):
    """Agent confirms the job was printed successfully."""
    device, err = _get_device(request)
    if err:
        return err

    try:
        job = PrintJob.objects.get(pk=job_id, device=device)
    except PrintJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found.'}, status=404)

    job.status = 'printed'
    job.printed_at = timezone.now()
    job.save(update_fields=['status', 'printed_at'])
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['POST'])
def job_fail(request, job_id):
    """Agent reports that printing failed."""
    device, err = _get_device(request)
    if err:
        return err

    try:
        job = PrintJob.objects.get(pk=job_id, device=device)
    except PrintJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found.'}, status=404)

    try:
        body = json.loads(request.body)
        error_msg = body.get('error', 'Unknown error')
    except Exception:
        error_msg = 'Unknown error'

    job.status = 'failed'
    job.error_message = error_msg
    job.save(update_fields=['status', 'error_message'])
    return JsonResponse({'ok': True})


# ─── Status check (used by Django UI) ────────────────────────────────────────

def device_status(request, device_id):
    """
    AJAX endpoint used by the POS terminal UI to check if the printer is ready
    before attempting to queue a print job. Returns JSON.
    """
    from tenants.mixins import get_tenant_or_404

    tenant = get_tenant_or_404(request)

    try:
        device = PrintDevice.objects.get(pk=device_id, tenant=tenant, is_active=True)
    except PrintDevice.DoesNotExist:
        return JsonResponse({'ready': False, 'reason': 'Device not found.'})

    device.refresh_online_status()

    return JsonResponse({
        'ready': device.is_ready,
        'online': device.is_online,
        'printer': device.printer_name,
        'last_seen': device.last_seen.isoformat() if device.last_seen else None,
        'reason': (
            'Agent is online and printer is detected.' if device.is_ready
            else ('Agent is offline.' if not device.is_online else 'No printer detected by agent.')
        ),
    })


# ─── Receipt text renderer ───────────────────────────────────────────────────

def build_receipt_text(sale, sys_settings, width=42):
    """
    Render a sale into plain-text receipt format.
    width=42 suits 80mm thermal paper. Use 32 for 58mm paper.

    Returns a multi-line string ready to send to any printer.
    """
    from settings_app.models import SystemSetting
    from django.utils import timezone as tz

    W = width
    divider = '─' * W
    thick   = '═' * W

    def center(text, w=W):
        return text.center(w)

    def ljust_rjust(left, right, w=W):
        space = w - len(left) - len(right)
        if space < 1:
            space = 1
        return left + ' ' * space + right

    lines = []

    # Header
    lines.append(thick)
    lines.append(center(sys_settings.business_name or 'GetCore POS'))
    if sys_settings.physical_address:
        for part in sys_settings.physical_address.split('\n'):
            lines.append(center(part.strip()))
    if sys_settings.contact_phone:
        lines.append(center(f'Tel: {sys_settings.contact_phone}'))
    if sys_settings.contact_email:
        lines.append(center(sys_settings.contact_email))
    lines.append(thick)

    # Sale metadata
    lines.append(f'Date   : {sale.created_at.strftime("%d %b %Y  %H:%M")}')
    lines.append(f'Receipt: #{sale.pk:06d}')
    if sale.invoice_number:
        lines.append(f'Invoice: {sale.invoice_number}')
    if sale.served_by:
        lines.append(f'Served : {sale.served_by.get_full_name() or sale.served_by.username}')
    if sale.customer:
        lines.append(f'Client : {sale.customer.name}')
    lines.append(divider)

    # Items
    col1_w = W - 10 - 8  # name | qty | amount
    lines.append(ljust_rjust(
        f'{"Item":<{col1_w}}{"Qty":>6}',
        f'{"Amount":>8}'
    ))
    lines.append(divider)

    currency = sys_settings.currency_symbol or 'KES'
    for item in sale.items.all():
        name = item.product_name[:col1_w]
        qty  = f'{item.quantity:>5.0f}'
        amt  = f'{item.line_total:>7.2f}'
        lines.append(ljust_rjust(f'{name:<{col1_w}}{qty}', amt))
        if item.discount_amount and item.discount_amount > 0:
            lines.append(f'  {"Discount":>{col1_w+5}} -{item.discount_amount:>7.2f}')

    lines.append(divider)

    # Totals
    lines.append(ljust_rjust('Subtotal', f'{sale.subtotal_amount:>8.2f}'))
    if sale.vat_amount and sale.vat_amount > 0:
        lines.append(ljust_rjust(f'VAT ({sys_settings.vat_rate:.0f}%)', f'{sale.vat_amount:>8.2f}'))
    if sale.discount_amount and sale.discount_amount > 0:
        lines.append(ljust_rjust('Discount', f'-{sale.discount_amount:>7.2f}'))
    lines.append(divider)
    lines.append(ljust_rjust('TOTAL', f'{currency} {sale.total_amount:>7.2f}'))
    lines.append(divider)

    # Payment
    lines.append(ljust_rjust('Payment', sale.get_payment_method_display()))
    if sale.amount_tendered and sale.amount_tendered > 0:
        lines.append(ljust_rjust('Tendered', f'{currency} {sale.amount_tendered:>7.2f}'))
        if sale.change_given and sale.change_given >= 0:
            lines.append(ljust_rjust('Change', f'{currency} {sale.change_given:>7.2f}'))
    if hasattr(sale, 'mpesa_code') and sale.mpesa_code:
        lines.append(f'Ref    : {sale.mpesa_code}')

    lines.append(thick)
    lines.append(center('Thank you for your business!'))
    if sys_settings.receipt_footer_text:
        for part in sys_settings.receipt_footer_text.split('\n'):
            lines.append(center(part.strip()))
    lines.append(thick)
    lines.append('')  # trailing newline for paper cut

    return '\n'.join(lines)


def queue_print_job(sale, tenant):
    """
    Helper used after a sale is completed.
    Finds the active print device for this tenant, renders the receipt,
    and creates a PrintJob. Silently skips if no device is configured or online.
    Returns the PrintJob (or None).
    """
    from settings_app.models import SystemSetting

    device = PrintDevice.objects.filter(
        tenant=tenant, is_active=True, is_online=True
    ).order_by('-last_seen').first()

    if not device:
        return None  # No active print agent — skip silently

    device.refresh_online_status()
    if not device.is_ready:
        return None  # Agent offline or no printer

    sys_settings = SystemSetting.get_settings(tenant)
    receipt_text = build_receipt_text(sale, sys_settings)

    job = PrintJob.objects.create(
        device=device,
        sale=sale,
        receipt_text=receipt_text,
        copies=1,
        status='pending',
    )
    return job
