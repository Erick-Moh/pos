"""users/turnstile.py — Cloudflare Turnstile server-side verification."""

import requests
from django.conf import settings


VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def verify_turnstile(token: str, remote_ip: str = '') -> bool:
    """Return True if the Turnstile token is valid."""
    secret = settings.TURNSTILE_SECRET_KEY
    if not secret:
        # Turnstile not configured — pass through (dev/testing)
        return True
    if not token:
        return False
    try:
        resp = requests.post(VERIFY_URL, data={
            'secret': secret,
            'response': token,
            'remoteip': remote_ip,
        }, timeout=5)
        return resp.json().get('success', False)
    except Exception:
        return False
