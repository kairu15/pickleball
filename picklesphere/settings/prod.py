"""Production settings.

Inherits everything from ``picklesphere.settings.base``, then re-derives
every setting that ``base`` computed from *its* DEBUG default. This matters:
``base`` reads ``.env`` via python-decouple, so a leftover ``DEBUG=True`` in
a deploy's ``.env`` must not leak wildcard hosts, disabled HSTS, or eager
Celery into a production process.

This module fails fast on insecure defaults so misconfiguration is caught at
boot rather than in production traffic. Use via ``DJANGO_ENV=prod`` or
``DJANGO_SETTINGS_MODULE=picklesphere.settings.prod``.
"""

from decouple import config

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import DATABASES, SECRET_KEY  # noqa: F401  (re-read below)

DEBUG = False

# ---------------------------------------------------------------------------
# Re-derive everything base computed from its own DEBUG value
# ---------------------------------------------------------------------------

# Hosts come strictly from the environment; no debug wildcards survive.
ALLOWED_HOSTS = [
    host.strip()
    for host in config('ALLOWED_HOSTS', default='').split(',')
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [config('SITE_URL', default='http://localhost:8000').rstrip('/')]

# Hashed (fingerprinted) static files served from STATIC_ROOT.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
    },
}
WHITENOISE_USE_FINDERS = False

# "On by default in production" security flags, still env-overridable.
# SECURE_SSL_REDIRECT assumes TLS terminates in front of Django; set it False
# when a load balancer or health check speaks plain HTTP to the app.
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# Celery must use a real broker in production, never inline execution.
CELERY_TASK_ALWAYS_EAGER = False

# Slow-query capture is a development/diagnostic tool; opt in explicitly.
CACHE_MONITOR_ENABLED = config('CACHE_MONITOR_ENABLED', default=False, cast=bool)

# Channels default to Redis in production (live scoring across workers).
CHANNEL_LAYER_BACKEND = config('CHANNEL_LAYER_BACKEND', default='redis').strip().lower()
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
if CHANNEL_LAYER_BACKEND == 'redis':
    try:
        import channels_redis  # noqa: F401

        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {'hosts': [config('REDIS_URL', default='redis://127.0.0.1:6379/0')]},
            },
        }
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# Fail fast on insecure configuration
# ---------------------------------------------------------------------------

_INSECURE_KEYS = {
    'django-insecure-ci-dev-key-not-for-production',
    'ci-secret-key-not-for-production-0000000000000000',
    'django-insecure-dev-key-not-for-production',
}
if SECRET_KEY in _INSECURE_KEYS or not SECRET_KEY:
    raise ImproperlyConfigured(
        'Refusing to start with a placeholder SECRET_KEY. Generate one with: '
        'python -c "import secrets; print(secrets.token_urlsafe(50))"'
    )

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['*']:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must list your production hostname(s); refusing to "
        "start with an empty or wildcard ('*') value."
    )

if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    raise ImproperlyConfigured(
        'SQLite is not supported in production. Set DB_ENGINE='
        'django.db.backends.postgresql and the DB_* variables (see '
        '.env.example and docker-compose.yml for a ready-made Postgres stack).'
    )

if not config('REDIS_URL', default=''):
    raise ImproperlyConfigured(
        'REDIS_URL must be set in production: Celery, the channel layer and '
        'the cache all expect Redis.'
    )
