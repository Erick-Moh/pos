"""core/exception_middleware.py — Catch unhandled exceptions and show a friendly error page."""

import logging
from django.db import IntegrityError, OperationalError, DatabaseError
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.messages import get_messages

logger = logging.getLogger(__name__)

FRIENDLY_MESSAGES = {
    'UNIQUE constraint failed': 'That record already exists. Please check for duplicates and try again.',
    'NOT NULL constraint': 'A required field is missing. Please fill in all required fields.',
    'FOREIGN KEY constraint': 'This record is linked to other data and cannot be changed that way.',
    'no such table': 'A database table is missing. Please contact your administrator.',
    'database is locked': 'The database is temporarily busy. Please try again in a moment.',
}


def _friendly_db_message(exc):
    msg = str(exc)
    for fragment, friendly in FRIENDLY_MESSAGES.items():
        if fragment.lower() in msg.lower():
            return friendly
    return 'A database error occurred. Please try again or contact your administrator.'


class AppExceptionMiddleware:
    """
    Catch unhandled exceptions across the entire app and render a clean error page
    instead of exposing Django's debug traceback to end users.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, (IntegrityError, OperationalError, DatabaseError)):
            logger.error('DB error on %s: %s', request.path, exception, exc_info=True)
            message = _friendly_db_message(exception)
            return self._error_response(request, message, status=400)

        # Let Django handle everything else (including its own 404/500 machinery)
        return None

    def _error_response(self, request, message, status=500):
        html = render_to_string('errors/app_error.html', {
            'error_message': message,
            'back_url': request.META.get('HTTP_REFERER', '/'),
        }, request=request)
        return HttpResponse(html, status=status)
