"""Object-level permission and audit tests for live scoring.

Matches expose participant data and a live score. Before this, any signed-in
user could read any match by id and ``match_score_api`` was anonymous, so these
tests pin the access rules and the score-edit audit trail.
"""

from datetime import time as dt_time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from reservations.models import Reservation
from scoring.models import Game, Match, ScoreAuditLog

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class MatchPermissionTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', password='Str0ng-Pickle-Pass!', role='user',
        )
        self.opponent = User.objects.create_user(
            username='opponent', password='Str0ng-Pickle-Pass!', role='user',
        )
        self.stranger = User.objects.create_user(
            username='stranger', password='Str0ng-Pickle-Pass!', role='user',
        )
        self.staff = User.objects.create_user(
            username='staff', password='Str0ng-Pickle-Pass!', role='staff',
        )
        site = Site.objects.create(name='Main Site')
        court = Court.objects.create(
            name='Court 1', site=site, hourly_rate=500, is_active=True,
        )
        self.reservation = Reservation.objects.create(
            user=self.owner, court=court,
            date=timezone.localdate() + timedelta(days=1),
            start_time=dt_time(9, 0), end_time=dt_time(10, 0),
            duration_hours=1, hourly_rate=500, subtotal=500, total_amount=500,
            status='confirmed',
        )
        self.match = Match.objects.create(
            reservation=self.reservation,
            team1_player1=self.owner,
            team2_player1=self.opponent,
            status='ongoing',
        )
        self.game = Game.objects.create(match=self.match, game_number=1)


class MatchAccessTests(MatchPermissionTestCase):
    def test_owner_can_open_the_match_detail(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('match_detail', args=[self.match.id]))

        self.assertEqual(response.status_code, 200)

    def test_player_can_open_the_match_detail(self):
        self.client.force_login(self.opponent)

        response = self.client.get(reverse('match_detail', args=[self.match.id]))

        self.assertEqual(response.status_code, 200)

    def test_stranger_is_denied_the_match_detail(self):
        self.client.force_login(self.stranger)

        response = self.client.get(
            reverse('match_detail', args=[self.match.id]), follow=True,
        )

        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('permission' in m.lower() for m in messages))

    def test_staff_can_open_any_match(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('match_detail', args=[self.match.id]))

        self.assertEqual(response.status_code, 200)

    def test_score_api_requires_login(self):
        response = self.client.get(reverse('match_score_api', args=[self.match.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_score_api_denies_a_stranger(self):
        self.client.force_login(self.stranger)

        response = self.client.get(reverse('match_score_api', args=[self.match.id]))

        self.assertEqual(response.status_code, 403)

    def test_score_api_allows_a_player(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('match_score_api', args=[self.match.id]))

        self.assertEqual(response.status_code, 200)

    def test_search_users_api_is_staff_only(self):
        self.client.force_login(self.stranger)

        response = self.client.get(reverse('search_users_api'))

        self.assertEqual(response.status_code, 302)


class ScoreAuditTests(MatchPermissionTestCase):
    def test_staff_score_update_writes_an_audit_row(self):
        self.client.force_login(self.staff)

        self.client.post(reverse('update_score', args=[self.game.id]), {
            'team': '1', 'action': 'add',
        })

        log = ScoreAuditLog.objects.get()
        self.assertEqual(log.match, self.match)
        self.assertEqual(log.changed_by, self.staff)
        self.assertEqual((log.old_team1_score, log.new_team1_score), (0, 1))
        self.assertEqual(log.source, 'staff')
