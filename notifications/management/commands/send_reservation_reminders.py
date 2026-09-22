"""
Management command to send reservation reminder emails 24 hours before bookings.
Should be scheduled via cron (e.g., every hour).
Usage: python manage.py send_reservation_reminders [--dry-run]
       python manage.py send_reservation_reminders --hours 2
"""
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError

from reservations.models import Reservation
from notifications.email_utils import send_reservation_reminder_email


class Command(BaseCommand):
    help = 'Send reservation reminder emails for upcoming bookings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview which reminders would be sent without actually sending',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours before the reservation to send the reminder (default: 24)',
        )


    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        hours_before = options.get('hours', 24)
        if hours_before < 1:
            raise CommandError('--hours must be at least 1.')

        # Calculate the target time window:
        # We want reservations that start exactly `hours_before` hours from now.
        # Use a +/- 30 minute window to account for cron scheduling imprecision
        # while avoiding duplicate sends on consecutive cron runs.
        now = timezone.localtime()
        target_start = now + timedelta(hours=hours_before)
        window_min = (target_start - timedelta(minutes=30)).time()
        window_max = (target_start + timedelta(minutes=30)).time()
        target_date = target_start.date()

        self.stdout.write(
            f'Searching for confirmed reservations on {target_date} '
            f'starting between {window_min.strftime("%H:%M")} and {window_max.strftime("%H:%M")}...'
        )

        # Find confirmed reservations that start roughly `hours_before` from now
        reservations = Reservation.objects.filter(
            status='confirmed',
            date=target_date,
            start_time__gte=window_min,
            start_time__lte=window_max,
        ).select_related('user', 'court').order_by('start_time')

        if not reservations:
            self.stdout.write(self.style.WARNING('No upcoming reservations found for reminders.'))
            return

        self.stdout.write(f'Found {reservations.count()} reservation(s) needing reminders.\n')

        sent_count = 0
        skipped_count = 0
        error_count = 0

        for reservation in reservations:
            user = reservation.user
            court = reservation.court

            if not user.email:
                self.stdout.write(
                    self.style.WARNING(f'  [SKIP] Reservation #{reservation.id}: user has no email')
                )
                skipped_count += 1
                continue

            if not user.is_active:
                self.stdout.write(
                    self.style.WARNING(f'  [SKIP] Reservation #{reservation.id}: user is inactive')
                )
                skipped_count += 1
                continue

            self.stdout.write(
                f'  {'[DRY-RUN]' if dry_run else '[SEND]'} '
                f'Reservation #{reservation.id}: {user.username} <{user.email}> '
                f'- {court.name} at {reservation.start_time.strftime("%I:%M %p")}'
            )

            if not dry_run:
                try:
                    success = send_reservation_reminder_email(user, reservation)
                    if success:
                        sent_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'    Failed to send email for Reservation #{reservation.id}')
                        )
                        error_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'    Error sending email for Reservation #{reservation.id}: {str(e)}'
                        )
                    )
                    error_count += 1

        # Summary
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'Dry run complete. Would send {reservations.count()} email(s).'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Complete! Sent: {sent_count}, Skipped: {skipped_count}, Errors: {error_count}'
                )
            )
