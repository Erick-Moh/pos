from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, business_name, contact_email, contact_name):
    """Send a plain welcome email to a new instance contact."""
    try:
        context = {
            'contact_name': contact_name,
            'business_name': business_name,
        }

        html_message = render_to_string('emails/welcome_email.html', context)

        text_message = (
            f"Welcome to GetCore POS\n\n"
            f"Hello {contact_name},\n\n"
            f'Your business "{business_name}" has been set up in GetCore POS.\n\n'
            f"You will receive a follow-up email with your login credentials and "
            f"getting-started instructions.\n\n"
            f"This is an automated message. Please do not reply.\n\n"
            f"(c) {timezone.now().year} GetCore POS. All rights reserved."
        )

        email = EmailMultiAlternatives(
            subject=f'Your GetCore POS Account — {business_name}',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact_email],
        )
        email.attach_alternative(html_message, 'text/html')
        result = email.send()

        return {
            'status': 'success',
            'business_name': business_name,
            'email': contact_email,
            'sent': result,
        }

    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            return {
                'status': 'failed',
                'business_name': business_name,
                'error': str(exc),
            }


# Keep legacy alias so any existing queued task names resolve
send_tenant_welcome_email = send_welcome_email
