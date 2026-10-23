# users/tasks.py

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id, username, credential_type, credential_value, business_name):
    try:
        user = User.objects.get(id=user_id)

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
            'business_name': business_name,
            'login_url': f'{settings.SITE_URL}/pos/',
        }

        html_message = render_to_string('emails/welcome_email.html', context)

        text_message = (
            f"Welcome to GetCore POS\n\n"
            f"Hello {context['first_name']},\n\n"
            f"Your account has been created. Here are your login credentials:\n\n"
            f"Business: {business_name}\n"
            f"Username: {username}\n"
            f"{credential_label}: {credential_value}\n\n"
            f"{credential_hint}\n\n"
            f"Sign in here: {context['login_url']}\n\n"
            f"This is an automated message. Please do not reply.\n\n"
            f"(c) {timezone.now().year} GetCore POS. All rights reserved."
        )

        email = EmailMultiAlternatives(
            subject='Welcome to GetCore POS - Your Account is Ready',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_message, 'text/html')
        result = email.send()

        return {'status': 'success', 'user_id': user_id, 'email': user.email, 'sent': result}

    except User.DoesNotExist:
        return {'status': 'error', 'message': f'User with ID {user_id} not found'}

    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            return {'status': 'failed', 'user_id': user_id, 'error': str(exc)}
