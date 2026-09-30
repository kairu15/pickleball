"""Tests for reservations.services — the race-safe booking primitives.

These functions are the single guard against double booking (MySQL has no
exclusion constraints) and equipment overselling. The tests pin the semantics
that concurrent checkout relies on: a slot is checked and consumed under a row
lock, and equipment stock can never go negative.
"""

from datetime import time as dt_time
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from equipment.models import Equipment
from reservations.models import Reservation, ReservationEquipment
from reservations.services import (
    SlotUnavailable,
    consume_equipment,
    create_reservation_atomic,
    ensure_slot_available,
    lock_court_and_ensure_available,
)

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class BookingServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='booker', password='Str0ng-Pickle-Pass!', role='user',
        )
        self.site = Site.objects.create(name='Main Site')
        self.court = Court.objects.create(
            name='Court 1', site=self.site, hourly_rate=500, is_active=True,
        )
        self.date = timezone.localdate() + timedelta(days=3)

    def reservation(self, start, end, status='confirmed', user=None):
        return Reservation.objects.create(
            user=user or self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat(start),
            end_time=dt_time.fromisoformat(end),
            duration_hours=2, hourly_rate=500, subtotal=1000, total_amount=1000,
            status=status,
        )

    def checkout_data(self, **overrides):
        payload = {
            'duration_hours': 2.0,
            'hourly_rate': 9999.0,  # deliberately wrong: the service must ignore it
            'subtotal': 19998.0,
            'equipment_ids': [],
            'notes': '',
            'match_format': 'singles',
            'game_type': 'friendly',
            'scoring_format': '11',
            'points_per_game': 11,
            'games_to_win': 2,
            'win_by_two': True,
        }
        payload.update(overrides)
        return payload


class SlotAvailabilityTests(BookingServiceTestCase):
    def test_overlapping_reservation_blocks_the_slot(self):
        self.reservation('10:00', '12:00')

        with self.assertRaises(SlotUnavailable):
            ensure_slot_available(
                self.court, self.date,
                dt_time.fromisoformat('09:00'), dt_time.fromisoformat('11:00'),
            )

    def test_adjacent_reservation_does_not_block_the_slot(self):
        self.reservation('11:00', '13:00')

        # Should not raise: ranges that merely touch are not an overlap.
        ensure_slot_available(
            self.court, self.date,
            dt_time.fromisoformat('09:00'), dt_time.fromisoformat('11:00'),
        )

    def test_cancelled_reservation_does_not_block_the_slot(self):
        self.reservation('10:00', '12:00', status='cancelled')

        ensure_slot_available(
            self.court, self.date,
            dt_time.fromisoformat('09:00'), dt_time.fromisoformat('11:00'),
        )

    def test_excluded_reservation_is_ignored(self):
        existing = self.reservation('10:00', '12:00')

        ensure_slot_available(
            self.court, self.date,
            dt_time.fromisoformat('09:00'), dt_time.fromisoformat('11:00'),
            exclude_reservation_id=existing.id,
        )

    def test_lock_court_and_ensure_available_raises_on_conflict(self):
        self.reservation('10:00', '12:00')

        with self.assertRaises(SlotUnavailable):
            lock_court_and_ensure_available(
                self.court, self.date,
                dt_time.fromisoformat('09:00'), dt_time.fromisoformat('11:00'),
            )


class ConsumeEquipmentTests(BookingServiceTestCase):
    def setUp(self):
        super().setUp()
        self.reservation_obj = self.reservation('08:00', '10:00')

    def test_decrements_stock_and_returns_the_fee(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Pro Paddle', rental_price=Decimal('75'),
            quantity_total=2, quantity_available=2,
        )

        fee = consume_equipment(self.reservation_obj, [paddle.id])

        self.assertEqual(fee, Decimal('75'))
        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 1)
        self.assertTrue(
            ReservationEquipment.objects.filter(
                reservation=self.reservation_obj, equipment=paddle,
            ).exists()
        )

    def test_out_of_stock_equipment_is_skipped(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Sold Out', rental_price=Decimal('75'),
            quantity_total=1, quantity_available=0,
        )

        fee = consume_equipment(self.reservation_obj, [paddle.id])

        self.assertEqual(fee, 0)
        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 0)
        self.assertFalse(ReservationEquipment.objects.exists())

    def test_missing_equipment_is_skipped_without_raising(self):
        fee = consume_equipment(self.reservation_obj, [999999])

        self.assertEqual(fee, 0)

    def test_duplicate_ids_consume_stock_only_once(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Pro Paddle', rental_price=Decimal('75'),
            quantity_total=2, quantity_available=2,
        )

        fee = consume_equipment(self.reservation_obj, [paddle.id, paddle.id])

        self.assertEqual(fee, Decimal('75'))
        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 1)
        self.assertEqual(ReservationEquipment.objects.count(), 1)


class CreateReservationAtomicTests(BookingServiceTestCase):
    def test_creates_a_pending_reservation_priced_from_the_court_rate(self):
        reservation = create_reservation_atomic(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat('09:00'),
            end_time=dt_time.fromisoformat('11:00'),
            checkout_data=self.checkout_data(),
        )

        self.assertEqual(reservation.status, 'pending')
        self.assertEqual(reservation.hourly_rate, Decimal('500'))
        self.assertEqual(reservation.subtotal, Decimal('1000'))
        self.assertEqual(reservation.total_amount, Decimal('1000'))

    def test_attaches_equipment_and_includes_the_fee_in_the_total(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Pro Paddle', rental_price=Decimal('50'),
            quantity_total=1, quantity_available=1,
        )

        reservation = create_reservation_atomic(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat('09:00'),
            end_time=dt_time.fromisoformat('11:00'),
            checkout_data=self.checkout_data(equipment_ids=[paddle.id]),
        )

        self.assertEqual(reservation.equipment_fee, Decimal('50'))
        self.assertEqual(reservation.total_amount, Decimal('1050'))
        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 0)

    def test_raises_and_rolls_back_when_the_slot_is_already_taken(self):
        self.reservation('09:00', '11:00')

        with self.assertRaises(SlotUnavailable):
            create_reservation_atomic(
                user=self.user, court=self.court, date=self.date,
                start_time=dt_time.fromisoformat('09:00'),
                end_time=dt_time.fromisoformat('11:00'),
                checkout_data=self.checkout_data(),
            )

        # Only the pre-existing reservation remains; equipment was not touched.
        self.assertEqual(Reservation.objects.count(), 1)

    def test_rolls_back_equipment_when_the_slot_conflicts(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Pro Paddle', rental_price=Decimal('50'),
            quantity_total=1, quantity_available=1,
        )
        self.reservation('09:00', '11:00')

        with self.assertRaises(SlotUnavailable):
            create_reservation_atomic(
                user=self.user, court=self.court, date=self.date,
                start_time=dt_time.fromisoformat('09:00'),
                end_time=dt_time.fromisoformat('11:00'),
                checkout_data=self.checkout_data(equipment_ids=[paddle.id]),
            )

        # The rollback must return the stock that was consumed before the clash.
        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 1)
        self.assertFalse(ReservationEquipment.objects.exists())
