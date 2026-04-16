from celery import shared_task
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def send_tenant_welcome_email(self, tenant_name, contact_email, contact_name):
    try:
        context = {
            'contact_name': contact_name,
            'tenant_name': tenant_name,
        }

        html_message = render_to_string('emails/tenant_welcome_email.html', context)

        text_message = f"""
Welcome to GetCore POS!

Hello {contact_name},

Great news! Your business "{tenant_name}" has been successfully created in our system.

We're setting up your account and will send you further communication via email soon with:
- Your login credentials
- Access instructions
- Getting started guide
- Support contact information

Please watch your inbox for our next email.

This is an automated message, please do not reply to this email.

© {timezone.now().year} GetCore POS. All rights reserved.
        """

        email = EmailMultiAlternatives(
            subject=f'Your GetCore POS Business Account Created - {tenant_name}',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact_email]
        )

        email.attach_alternative(html_message, "text/html")
        result = email.send()

        return {
            'status': 'success',
            'tenant_name': tenant_name,
            'email': contact_email,
            'sent': result
        }

    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            return {
                'status': 'failed',
                'tenant_name': tenant_name,
                'error': str(exc)
            }


# ════════════════════════════════════════════════════════════════════════
#  TENANT SUBSCRIPTION / BILLING TASKS
#  These run on a Celery Beat schedule (configured via django-celery-beat
#  admin or the CELERY_BEAT_SCHEDULE dict in settings.py).
# ════════════════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=3)
def deactivate_expired_trial_tenants(self):
    """
    Daily task: find all trial tenants whose trial_ends_on has elapsed
    and mark them inactive.
    Schedule: every day at 01:00 Africa/Nairobi (add via Beat admin).
    """
    from tenants.models import Tenant
    from .models import Notification
    today = timezone.now().date()
    expired = Tenant.objects.filter(
        plan='trial',
        is_active=True,
        trial_ends_on__lt=today,
    )
    deactivated = []
    for tenant in expired:
        tenant.is_active = False
        tenant.save(update_fields=['is_active', 'updated_at'])
        deactivated.append(tenant.reference_code)
        # In-system notifications
        Notification.create_for_tenant(
            tenant=tenant,
            notification_type='trial_ended',
            title='Your free trial has ended',
            message=(
                f'Your 30-day free trial expired on {today.strftime("%d %B %Y")}. '
                f'Your account has been temporarily locked. To restore access, '
                f'please pay the monthly maintenance fee of KES {tenant.monthly_fee:,.0f}.'
            ),
            action_url=f'/{tenant.slug}/billing/checkout/',
        )
        Notification.create_for_platform(
            tenant=tenant,
            notification_type='trial_expired_admin',
            title=f'Trial expired: {tenant.name}',
            message=(
                f'Client "{tenant.name}" (Ref: {tenant.reference_code}) trial expired on '
                f'{today.strftime("%d %B %Y")}. Account auto-locked.'
            ),
            action_url=f'/platform/clients/{tenant.pk}/',
        )
        if tenant.owner_email:
            _send_account_deactivation_email(tenant)
    return {'deactivated': deactivated, 'count': len(deactivated)}


@shared_task(bind=True, max_retries=3)
def deactivate_unpaid_tenants(self):
    """
    Daily task: deactivate paid-plan tenants whose payment_due_date has elapsed.
    Schedule: every day at 01:15 Africa/Nairobi.
    """
    from tenants.models import Tenant
    from .models import Notification
    today = timezone.now().date()
    overdue = Tenant.objects.filter(
        is_active=True,
        payment_due_date__lt=today,
    ).exclude(plan='trial')
    deactivated = []
    for tenant in overdue:
        tenant.is_active = False
        tenant.save(update_fields=['is_active', 'updated_at'])
        deactivated.append(tenant.reference_code)
        Notification.create_for_tenant(
            tenant=tenant,
            notification_type='account_deactivated',
            title='Account locked — maintenance fee overdue',
            message=(
                f'Your GetCore account has been suspended because the monthly maintenance '
                f'fee of KES {tenant.monthly_fee:,.0f} was not received by {today.strftime("%d %B %Y")}. '
                f'Please make payment to restore full access immediately.'
            ),
            action_url=f'/{tenant.slug}/billing/checkout/',
        )
        Notification.create_for_platform(
            tenant=tenant,
            notification_type='payment_defaulted',
            title=f'Payment defaulted: {tenant.name}',
            message=(
                f'Client "{tenant.name}" (Ref: {tenant.reference_code}) has defaulted on their '
                f'KES {tenant.monthly_fee:,.0f} monthly fee. Account auto-locked on {today.strftime("%d %B %Y")}.'
            ),
            action_url=f'/platform/clients/{tenant.pk}/',
        )
        if tenant.owner_email:
            _send_account_deactivation_email(tenant)
    return {'deactivated': deactivated, 'count': len(deactivated)}


@shared_task(bind=True, max_retries=3)
def send_trial_expiry_reminders(self):
    """
    Daily task: send reminder emails + in-system notifications to trial tenants
    whose trial expires in exactly 5 days or exactly 2 days.
    Schedule: every day at 08:00 Africa/Nairobi.
    """
    from tenants.models import Tenant
    from .models import Notification
    today = timezone.now().date()
    reminders_sent = []

    for days_left in [5, 2]:
        target_date = today + timezone.timedelta(days=days_left)
        tenants_expiring = Tenant.objects.filter(
            plan='trial',
            is_active=True,
            trial_ends_on=target_date,
        )

        for tenant in tenants_expiring:
            ntype = 'trial_expiry_5d' if days_left == 5 else 'trial_expiry_2d'
            Notification.create_for_tenant(
                tenant=tenant,
                notification_type=ntype,
                title=f'Trial expires in {days_left} day{"s" if days_left > 1 else ""}',
                message=(
                    f'Your free trial ends on {tenant.trial_ends_on.strftime("%d %B %Y")} '
                    f'({days_left} day{"s" if days_left > 1 else ""} remaining). '
                    f'Subscribe to a paid plan (KES {tenant.monthly_fee:,.0f}/month) to continue '
                    f'without interruption. One-time installation: KES 15,000.'
                ),
                action_url=f'/{tenant.slug}/billing/checkout/',
            )
            # Email reminder
            if tenant.owner_email:
                try:
                    subject = (
                        f'GetCore trial expires in {days_left} day{"s" if days_left > 1 else ""} — {tenant.name}'
                    )
                    body = (
                        f'Hello {tenant.owner_name or "there"},\n\n'
                        f'Your free trial for "{tenant.name}" expires on '
                        f'{tenant.trial_ends_on.strftime("%d %B %Y")} ({days_left} day{"s" if days_left > 1 else ""} remaining).\n\n'
                        f'Subscribe now to keep your data and continue using GetCore:\n'
                        f'  Monthly maintenance: KES {tenant.monthly_fee:,.0f}/month\n'
                        f'  One-time installation: KES 15,000\n\n'
                        f'Contact us to upgrade:\n'
                        f'  Email: support@getcore.co.ke\n'
                        f'  Phone: +254 700 000 000\n\n'
                        f'© {timezone.now().year} GetCore Solutions.'
                    )
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[tenant.owner_email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            reminders_sent.append({'tenant': tenant.reference_code, 'days_left': days_left})

    return {'reminders_sent': reminders_sent, 'count': len(reminders_sent)}


def _send_account_deactivation_email(tenant):
    """Helper: notify tenant owner their account has been deactivated."""
    subject = f'Your GetCore account has been deactivated — {tenant.name}'
    body = (
        f'Hello {tenant.owner_name or "there"},\n\n'
        f'Your GetCore POS account for "{tenant.name}" has been deactivated because '
        f'the payment deadline has elapsed.\n\n'
        f'To reactivate your account and restore access, please contact us:\n'
        f'  Email: support@getcore.co.ke\n'
        f'  Phone: +254 700 000 000\n\n'
        f'Your data is safe and will be restored upon payment.\n\n'
        f'© {timezone.now().year} GetCore Solutions.'
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tenant.owner_email],
            fail_silently=True,
        )
    except Exception:
        pass