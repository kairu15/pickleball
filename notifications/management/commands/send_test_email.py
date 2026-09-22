"""
Management command to send a test email to verify email configuration.
Usage: python manage.py send_test_email <user_id_or_email>
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from notifications.email_utils import send_test_email


class Command(BaseCommand):
    help = 'Send a test email to verify email configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            help='User ID or email address of the recipient'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Send test email to all super admins',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        recipient = options.get('recipient')
        send_all = options.get('all')

        users = []

        if send_all:
            users = User.objects.filter(is_active=True, role='super_admin')
            if not users:
                self.stdout.write(self.style.WARNING('No super admins found.'))
                return
        elif recipient:
            if recipient.isdigit():
                try:
                    user = User.objects.get(id=recipient)
                    users = [user]
                except User.DoesNotExist:
                    raise CommandError(f'User with ID {recipient} not found.')
            else:
                try:
                    user = User.objects.get(email=recipient)
                    users = [user]
                except User.DoesNotExist:
                    raise CommandError(f'User with email {recipient} not found.')
        else:
            # Default: send to first super admin
            user = User.objects.filter(is_active=True, role='super_admin').first()
            if not user:
                raise CommandError('No active super admin found. Provide a recipient or use --all.')
            users = [user]

        for user in users:
            if not user.email:
                self.stdout.write(self.style.WARNING(f'User {user.username} has no email. Skipping.'))
                continue
            success = send_test_email(user)
            if success:
                self.stdout.write(self.style.SUCCESS(f'Test email sent to {user.username} <{user.email}>'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to send test email to {user.username} <{user.email}>'))
