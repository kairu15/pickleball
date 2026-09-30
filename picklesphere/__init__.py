# Apply Django compatibility patches for newer Python versions
from . import django_patch

# Expose the Celery app so `celery -A picklesphere worker` works. Guarded so
# the app boots in development and tests where celery is not installed.
try:
    from .celery import app as celery_app
except ImportError:  # celery (or its config) is not available
    celery_app = None

__all__ = ('celery_app',)
