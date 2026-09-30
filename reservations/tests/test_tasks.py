"""Tests for the reservation Celery tasks.

The task is invoked directly (not via ``.delay``) so the test does not need a
broker; this exercises the same code path Celery runs on a worker.
"""

from datetime import time as dt_time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from reservations.models import Reservation
from reservations.tasks import expire_unpaid_reservations

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ExpireUnpaidReservationsTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='taskuser', password='Str0ng-Pickle-Pass!', role='user',
        )
        site = Site.objects.create(name='Main Site')
        self.court = Court.objects.create(
            name='Court 1', site=site, hourly_rate=500, is_active=True,
        )
        self.reservation = Reservation.objects.create(
            user=self.user, court=self.court,
            date=timezone.localdate() + timedelta(days=2),
            start_time=dt_time(9, 0), end_time=dt_time(11, 0),
            duration_hours=2, hourly_rate=500, subtotal=1000, total_amount=1000,
            status='pending',
        )
        Reservation.objects.filter(pk=self.reservation.pk).update(
            created_at=timezone.now() - timedelta(minutes=60),
        )

    def test_task_expires_stale_unpaid_reservations(self):
        result = expire_unpaid_reservations(minutes=30)

        self.assertEqual(result, [self.reservation.id])
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'cancelled')
