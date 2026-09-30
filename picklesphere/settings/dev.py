"""Development settings.

Inherits everything from ``picklesphere.settings.base`` and turns on the
conveniences a local developer expects. ``base`` computes a handful of
settings from its own ``DEBUG=False`` default, so this module re-derives the
ones that must follow ``DEBUG=True`` explicitly.
"""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']

# DEV-only conveniences: wildcard ngrok hosts so tunnels work out of the box.
CSRF_TRUSTED_ORIGINS += [
    'http://127.0.0.1:8000', 'http://localhost:8000',
    'http://127.0.0.1:8001', 'http://localhost:8001',
    'https://*.ngrok-free.app', 'https://*.ngrok-free.dev',
    'https://*.ngrok.io', 'https://*.ngrok.app',
]

# Unhashed static files served from the finders in dev (base enables
# ManifestStaticFilesStorage only for production).
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
WHITENOISE_USE_FINDERS = True

# base derived these "on when DEBUG=False"; relax them for plain-HTTP dev.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Run Celery tasks inline in dev so no broker is needed.
CELERY_TASK_ALWAYS_EAGER = True

# Slow-query capture for the Cache Monitor page.
CACHE_MONITOR_ENABLED = True

# Channels stay on the in-memory layer in dev (base honours
# CHANNEL_LAYER_BACKEND=redis if you want to exercise Redis locally).
