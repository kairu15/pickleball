import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tournaments.models import Tournament, Registration

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate sample pending registrations for a tournament'

    def add_arguments(self, parser):
        parser.add_argument('tournament_id', type=int, help='Tournament ID')
        parser.add_argument('--count', type=int, default=32, help='Number of registrations to create (default: 32)')

    def handle(self, *args, **options):
        tournament_id = options['tournament_id']
        count = options['count']

        try:
            tournament = Tournament.objects.get(pk=tournament_id)
        except Tournament.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Tournament with ID {tournament_id} not found'))
            return

        self.stdout.write(f'Generating {count} pending registrations for tournament: {tournament.name}')

        skill_levels = ['beginner', 'intermediate', 'advanced']
        genders = ['male', 'female', 'other']

        created = 0
        skipped = 0

        for i in range(count):
            # Generate unique username
            base_username = f'sample_player_{i+1}'
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}_{suffix}'
                suffix += 1

            # Create user
            user = User.objects.create(
                username=username,
                email=f'{username}@example.com',
                first_name=f'Player{i+1}',
                last_name='Sample',
                is_active=True
            )
            user.set_password('password123')
            user.save()

            # Check if registration already exists
            if Registration.objects.filter(tournament=tournament, user=user).exists():
                skipped += 1
                continue

            # Create pending registration
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status='pending',
                skill_level=random.choice(skill_levels),
                gender=random.choice(genders)
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created} pending registrations'))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped} (already registered)'))
