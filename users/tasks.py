# users/tasks.py

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id, username, credential_type, credential_value, tenant_name, tenant_slug):
    try:
        user = User.objects.get(id=user_id)

        # Determine credential label based on type
        if credential_type == 'pin':
            credential_label = 'PIN'
            credential_hint = 'You will be prompted to change your PIN on first login.'
        else:
            credential_label = 'Password'
            credential_hint = 'You will be prompted to change your password on first login.'

        context = {
            'first_name': user.first_name or username,
            'username': username,
            'credential_type': credential_label,
            'credential_value': credential_value,
            'credential_hint': credential_hint,
            'tenant_name': tenant_name,
            'tenant_slug': tenant_slug,
            'login_url': f'{settings.SITE_URL}/{tenant_slug}/pos/',
        }

        html_message = render_to_string('emails/welcome_email.html', context)

        text_message = f"""
Welcome to GetCore POS

Hello {context['first_name']},

Your account has been created successfully. Here are your login credentials:

Business Name: {tenant_name}
Username: {username}
{credential_label}: {credential_value}

You'll be prompted to change this on your first login.

Sign in here: {context['login_url']}

IMPORTANT: For security, change your credentials immediately after your first login.

Next Steps:
1. Sign in using the credentials above
2. Change your {credential_label.lower()} when prompted
3. Complete your profile
4. Start using GetCore POS

This is an automated message, please do not reply to this email.

© {timezone.now().year} GetCore POS. All rights reserved.
        """

        email = EmailMultiAlternatives(
            subject='Welcome to GetCore POS - Your Account is Ready',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )

        email.attach_alternative(html_message, "text/html")
        result = email.send()

        return {
            'status': 'success',
            'user_id': user_id,
            'email': user.email,
            'sent': result
        }

    except User.DoesNotExist:
        return {
            'status': 'error',
            'message': f'User with ID {user_id} not found'
        }

    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            return {
                'status': 'failed',
                'user_id': user_id,
                'error': str(exc)
            }
