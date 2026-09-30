"""Celery tasks for notifications.

Wraps the existing management commands so they can be scheduled by Celery beat
instead of needing an external cron.
"""

from celery import shared_task
from django.core.management import call_command


@shared_task(name='notifications.send_reservation_reminders')
def send_reservation_reminders(hours=24):
    """Send reminder emails for confirmed bookings starting in ``hours``."""
    call_command('send_reservation_reminders', '--hours', hours)
