"""Tests for court maintenance blocks and closure notices.

Covers: the model's ``covers()`` logic, the booking gate in
``reservations.services`` (slot APIs, verify API, and the atomic create all
flow through it), slot surfacing, auto-cancellation of overlapped
reservations with notifications, waitlist cleanup, and the admin CRUD UI.
"""

from datetime import time as dt_time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from courts.models import Court, CourtMaintenanceBlock, Site
from equipment.models import Equipment
from notifications.models import Notification
from reservations.models import Reservation, WaitlistEntry
from reservations.services import (
    SlotUnavailable,
    cancel_reservations_for_block,
    create_reservation_atomic,
    ensure_slot_available,
)

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


def tzdt(*args):
    """Aware datetime in the project timezone, for building block windows."""
    return timezone.make_aware(timezone.datetime(*args))


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class MaintenanceBlockTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='Str0ng-Pickle-Pass!', role='super_admin',
        )
        self.member = User.objects.create_user(
            username='member', password='Str0ng-Pickle-Pass!', role='user',
        )
        site = Site.objects.create(name='Main Site')
        self.court = Court.objects.create(
            name='Court 1', site=site, hourly_rate=500, is_active=True,
        )
        self.date = timezone.localdate() + timedelta(days=3)

    def block(self, day_offset=3, start_hour=9, end_hour=12, block_type='maintenance'):
        start = tzdt(
            (self.date + timedelta(days=day_offset - 3)).year,
            (self.date + timedelta(days=day_offset - 3)).month,
            (self.date + timedelta(days=day_offset - 3)).day,
            start_hour, 0,
        )
        return CourtMaintenanceBlock.objects.create(
            court=self.court,
            block_type=block_type,
            reason='Resurfacing the playing surface',
            start_datetime=start,
            end_datetime=start + timedelta(hours=end_hour - start_hour),
        )

    def book(self, start='09:00', end='11:00', status='confirmed', user=None):
        return Reservation.objects.create(
            user=user or self.member, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat(start),
            end_time=dt_time.fromisoformat(end),
            duration_hours=2, hourly_rate=500, subtotal=1000, total_amount=1000,
            status=status,
        )


class CoversTests(MaintenanceBlockTestCase):
    def test_covers_overlapping_booking_window(self):
        block = self.block(start_hour=9, end_hour=12)
        self.assertTrue(block.covers(self.date, dt_time(10, 0), dt_time(11, 0)))

    def test_covers_touching_edges_do_not_overlap(self):
        block = self.block(start_hour=9, end_hour=12)
        self.assertFalse(block.covers(self.date, dt_time(12, 0), dt_time(14, 0)))
        self.assertFalse(block.covers(self.date, dt_time(7, 0), dt_time(9, 0)))

    def test_day_level_coverage(self):
        block = self.block()
        self.assertTrue(block.covers(self.date))
        self.assertFalse(block.covers(self.date + timedelta(days=1)))


class BookingGateTests(MaintenanceBlockTestCase):
    def test_ensure_slot_available_raises_for_blocked_slot(self):
        self.block(start_hour=9, end_hour=12)
        with self.assertRaises(SlotUnavailable):
            ensure_slot_available(self.court, self.date, dt_time(10, 0), dt_time(11, 0))

    def test_ensure_slot_available_allows_adjacent_slot(self):
        self.block(start_hour=9, end_hour=12)
        ensure_slot_available(self.court, self.date, dt_time(12, 0), dt_time(14, 0))

    def test_blocked_slot_rejects_atomic_booking(self):
        self.block(start_hour=9, end_hour=12)
        with self.assertRaises(SlotUnavailable):
            create_reservation_atomic(
                user=self.member, court=self.court, date=self.date,
                start_time=dt_time(10, 0), end_time=dt_time(11, 0),
                checkout_data={},
            )

    def test_closure_type_also_blocks(self):
        self.block(block_type='closure')
        with self.assertRaises(SlotUnavailable):
            ensure_slot_available(self.court, self.date, dt_time(10, 0), dt_time(11, 0))


class SlotSurfaceTests(MaintenanceBlockTestCase):
    def test_build_time_slots_marks_blocked_slots_unavailable(self):
        from courts.views import _build_time_slots

        self.block(start_hour=9, end_hour=12)
        slots = _build_time_slots(self.court, self.date)
        nine = next(s for s in slots if s['start'] == '09:00')
        twelve = next(s for s in slots if s['start'] == '12:00')
        self.assertFalse(nine['available'])
        self.assertEqual(nine['status'], 'unavailable')
        self.assertTrue(twelve['available'])

    def test_monthly_availability_api_marks_blocked_day_full(self):
        self.client.force_login(self.admin)
        self.block(start_hour=8, end_hour=24)  # covers the whole booking day
        response = self.client.get(
            reverse('get_monthly_availability'),
            {'court_id': self.court.id, 'month': self.date.month, 'year': self.date.year},
        )
        data = response.json()
        self.assertEqual(data['availability'][self.date.isoformat()], 'full')

    def test_verify_slot_api_rejects_blocked_slot(self):
        self.client.force_login(self.admin)
        self.block(start_hour=9, end_hour=12)
        response = self.client.get(
            reverse('verify_slot'),
            {
                'court_id': self.court.id, 'date': self.date.isoformat(),
                'start': '10:00', 'end': '11:00',
            },
        )
        data = response.json()
        self.assertFalse(data['available'])
        self.assertIn('unavailable', data['message'])


class AutoCancelTests(MaintenanceBlockTestCase):
    def test_overlapped_reservations_are_cancelled_and_notified(self):
        reservation = self.book('09:00', '11:00')
        adjacent = self.book('12:00', '14:00')
        block = self.block(start_hour=9, end_hour=12)

        cancelled = cancel_reservations_for_block(block)

        self.assertEqual(cancelled, [reservation.id])
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')
        adjacent.refresh_from_db()
        self.assertEqual(adjacent.status, 'confirmed')
        self.assertTrue(
            Notification.objects.filter(
                user=self.member, category='maintenance',
            ).exists()
        )

    def test_pending_reservation_payment_is_failed(self):
        from payments.models import Payment

        reservation = self.book(status='pending')
        Payment.objects.create(reservation=reservation, amount=1000, status='pending')
        block = self.block()

        cancel_reservations_for_block(block)

        payment = Payment.objects.get(reservation=reservation)
        self.assertEqual(payment.status, 'failed')

    def test_equipment_is_returned_to_stock(self):
        equipment = Equipment.objects.create(
            name='Paddle', quantity_available=2, rental_price=50, is_active=True,
        )
        reservation = self.book()
        reservation.rented_equipment.create(
            equipment=equipment, quantity=1, rental_fee=50,
        )
        block = self.block()

        cancel_reservations_for_block(block)

        equipment.refresh_from_db()
        self.assertEqual(equipment.quantity_available, 3)

    def test_waitlist_entries_for_blocked_days_are_cancelled(self):
        self.book('09:00', '11:00')
        WaitlistEntry.objects.create(
            user=self.member, court=self.court, date=self.date,
            start_time=dt_time(9, 0), end_time=dt_time(11, 0), status='waiting',
        )
        block = self.block()

        cancel_reservations_for_block(block)

        self.assertFalse(
            WaitlistEntry.objects.filter(status__in=['waiting', 'notified']).exists()
        )

    def test_idempotent_no_double_cancel_or_double_notify(self):
        reservation = self.book()
        block = self.block()

        cancel_reservations_for_block(block)
        cancel_reservations_for_block(block)

        self.assertEqual(
            Notification.objects.filter(user=self.member, category='maintenance').count(),
            1,
        )
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')

    def test_email_helper_failure_does_not_break_cancellation(self):
        from unittest.mock import patch

        reservation = self.book()
        block = self.block()
        with patch(
            'notifications.email_utils.send_reservation_cancelled_email',
            side_effect=RuntimeError('smtp down'),
        ):
            with self.assertRaises(RuntimeError):
                cancel_reservations_for_block(block)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')


class AdminUITests(MaintenanceBlockTestCase):
    def test_admin_can_create_block_and_reservations_are_cancelled(self):
        self.book('09:00', '11:00')
        self.client.force_login(self.admin)
        start = f'{self.date.isoformat()}T09:00'
        end = f'{self.date.isoformat()}T12:00'
        response = self.client.post(
            reverse('admin_maintenance_create'),
            {
                'court': self.court.id,
                'block_type': 'maintenance',
                'reason': 'Resurfacing',
                'start_datetime': start,
                'end_datetime': end,
            },
        )
        self.assertEqual(CourtMaintenanceBlock.objects.count(), 1)
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.status, 'cancelled')

    def test_create_rejects_end_before_start(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin_maintenance_create'),
            {
                'court': self.court.id,
                'block_type': 'maintenance',
                'reason': 'Bad window',
                'start_datetime': f'{self.date.isoformat()}T12:00',
                'end_datetime': f'{self.date.isoformat()}T09:00',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourtMaintenanceBlock.objects.count(), 0)

    def test_non_admin_cannot_access(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('admin_maintenance_list'))
        self.assertIn(response.status_code, (302, 403))

    def test_list_and_delete(self):
        block = self.block()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_maintenance_list'))
        self.assertContains(response, 'Resurfacing')
        self.client.post(reverse('admin_maintenance_delete', args=[block.id]))
        self.assertFalse(
            CourtMaintenanceBlock.objects.filter(id=block.id).exists()
        )


class CourtDetailNoticeTests(MaintenanceBlockTestCase):
    def test_upcoming_block_shown_on_court_detail(self):
        self.block()
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('court_detail', args=[self.court.id])
        )
        self.assertContains(response, 'Upcoming Maintenance')
