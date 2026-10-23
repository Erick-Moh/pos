"""
GetCore ERP - Core Django Settings
Django settings for the GetCore POS System.
"""

from pathlib import Path
import json

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / 'config.json') as config_file:
    config = json.load(config_file)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config['DEBUG']

ALLOWED_HOSTS = config['ALLOWED_HOSTS']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.humanize',
    'django_celery_results',
    'django_celery_beat',

    # GetCore Apps
    'platform_app',
    'users',
    'inventory',
    'pos',
    'finance',
    'settings_app',
    'backups',
]

MIDDLEWARE = [
    'core.exception_middleware.AppExceptionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Force users to change credentials on first login
    'users.middleware.ForceCredentialChangeMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom context processors
                'settings_app.context_processors.system_settings',
                'platform_app.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

if DEBUG:
    # Database - SQLite for easy deployment and development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # In production, use environment variables or config.json for DB settings
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config['DB_NAME'],
            'USER': config['DB_USER'],
            'PASSWORD': config['DB_PASSWORD'],
            'HOST': config['DB_HOST'],
            'PORT': config['DB_PORT'],
        }
    }
# Custom User Model
AUTH_USER_MODEL = 'users.GetCoreUser'

# Authentication Backends - supports both PIN (staff) and Password (admin) login
AUTHENTICATION_BACKENDS = [
    'users.backends.PinAuthBackend',     # Staff: username + 4-digit PIN
    'users.backends.AdminAuthBackend',   # Admin: username + strong password
    'django.contrib.auth.backends.ModelBackend',  # Fallback
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'  # Kenya Standard Time (EAT, UTC+3)
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Uploaded logos, images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login / Logout
LOGIN_URL = '/login/'
DEFAULT_USER_PASSWORD = config['DEFAULT_USER_PASSWORD']
DEFAULT_USER_PIN = config['DEFAULT_USER_PIN']
SITE_URL = config['SITE_URL']


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config['EMAIL_HOST']
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = config['EMAIL_HOST_PASSWORD']
DEFAULT_FROM_EMAIL = config['DEFAULT_FROM_EMAIL']

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

APPEND_SLASH = False


CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TASK_DEFAULT_QUEUE = "getcore"
CELERY_TIMEZONE = "Africa/Nairobi"
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# ── Cloudflare Turnstile ────────────────────────────────────────────────
TURNSTILE_SITE_KEY   = config.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = config.get('TURNSTILE_SECRET_KEY', '')

# ── Celery Beat Schedule ────────────────────────────────────────────────
# Manage periodic tasks via Django admin → Periodic Tasks (django-celery-beat).
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'nightly-backup': {
        'task': 'backups.tasks.nightly_backup',
        'schedule': crontab(hour=0, minute=0),
    },
}
