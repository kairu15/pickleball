"""Celery tasks for reservations.

Thin wrappers around the tested service functions so the same logic runs from
a management command, a cron job, or Celery beat. See ``CELERY_BEAT_SCHEDULE``
in settings.
"""

from celery import shared_task


@shared_task(name='reservations.expire_unpaid_reservations')
def expire_unpaid_reservations(minutes=30):
    """Cancel unpaid reservation holds older than ``minutes``."""
    from .services import expire_stale_pending_reservations

    return expire_stale_pending_reservations(older_than_minutes=minutes)
