"""Tests for expiring abandoned unpaid reservation holds."""

from datetime import time as dt_time
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from equipment.models import Equipment
from notifications.models import Notification
from payments.models import Payment
from reservations.models import Reservation, ReservationEquipment, WaitlistEntry
from reservations.services import expire_stale_pending_reservations

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ExpireUnpaidReservationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='holduser', password='Str0ng-Pickle-Pass!', role='user',
        )
        site = Site.objects.create(name='Main Site')
        self.court = Court.objects.create(
            name='Court 1', site=site, hourly_rate=500, is_active=True,
        )
        self.date = timezone.localdate() + timedelta(days=3)

    def pending(self, start='09:00', end='11:00', age_minutes=60):
        reservation = Reservation.objects.create(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat(start), end_time=dt_time.fromisoformat(end),
            duration_hours=2, hourly_rate=500, subtotal=1000, total_amount=1000,
            status='pending',
        )
        Reservation.objects.filter(pk=reservation.pk).update(
            created_at=timezone.now() - timedelta(minutes=age_minutes),
        )
        return reservation

    def test_old_pending_reservation_is_cancelled(self):
        reservation = self.pending()

        expired = expire_stale_pending_reservations(older_than_minutes=30)

        self.assertEqual(expired, [reservation.id])
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')

    def test_recent_pending_reservation_is_left_alone(self):
        reservation = self.pending(age_minutes=5)

        expired = expire_stale_pending_reservations(older_than_minutes=30)

        self.assertEqual(expired, [])
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'pending')

    def test_paid_reservation_is_never_expired(self):
        reservation = self.pending()
        Payment.objects.create(
            reservation=reservation, amount=1000, status='paid',
        )

        expired = expire_stale_pending_reservations(older_than_minutes=30)

        self.assertEqual(expired, [])
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'pending')

    def test_pending_payment_is_marked_failed(self):
        reservation = self.pending()
        payment = Payment.objects.create(
            reservation=reservation, amount=1000, status='pending',
        )

        expire_stale_pending_reservations(older_than_minutes=30)

        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')

    def test_equipment_is_returned_to_stock(self):
        reservation = self.pending()
        paddle = Equipment.objects.create(
            type='paddle', name='Paddle', rental_price=50,
            quantity_total=2, quantity_available=1, quantity_reserved=1,
        )
        ReservationEquipment.objects.create(
            reservation=reservation, equipment=paddle, quantity=1, rental_fee=50,
        )

        expire_stale_pending_reservations(older_than_minutes=30)

        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 2)

    def test_waitlisted_user_is_notified_when_the_slot_expires(self):
        reservation = self.pending()
        WaitlistEntry.objects.create(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat('09:00'),
            end_time=dt_time.fromisoformat('11:00'),
            status='waiting',
        )

        expire_stale_pending_reservations(older_than_minutes=30)

        self.assertTrue(Notification.objects.filter(title='Slot Available!').exists())

    def test_management_command_runs(self):
        self.pending()

        call_command('expire_unpaid_reservations', '--minutes', '30')

        self.assertEqual(
            Reservation.objects.filter(status='cancelled').count(), 1,
        )
