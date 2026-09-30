"""Cancel unpaid reservation holds that have expired.

Intended to run on a schedule (cron, or Celery beat via
``reservations.tasks.expire_unpaid_reservations``). See AUDIT.md H4.
"""

from django.core.management.base import BaseCommand

from reservations.services import expire_stale_pending_reservations

DEFAULT_HOLD_MINUTES = 30


class Command(BaseCommand):
    help = (
        'Cancel pending reservations whose unpaid hold has expired, returning '
        'their equipment to stock and offering the slot to the waitlist.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=DEFAULT_HOLD_MINUTES,
            help=f'Hold window in minutes (default: {DEFAULT_HOLD_MINUTES}).',
        )

    def handle(self, *args, **options):
        minutes = options['minutes']
        expired = expire_stale_pending_reservations(older_than_minutes=minutes)
        self.stdout.write(
            self.style.SUCCESS(
                f'Expired {len(expired)} unpaid reservation(s) older than '
                f'{minutes} minutes. IDs: {expired or "-"}'
            )
        )
