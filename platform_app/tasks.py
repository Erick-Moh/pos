from celery import shared_task
from django.core.mail import EmailMultiAlternatives
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
        