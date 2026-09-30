"""Tests for the waitlist: join rules, auto-notify on release, and claiming."""

from datetime import time as dt_time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from notifications.models import Notification
from reservations.models import Reservation, WaitlistEntry
from reservations.services import (
    WaitlistError,
    create_reservation_atomic,
    join_waitlist,
    release_slot_and_notify_waitlist,
)

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class WaitlistServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='waiter', password='Str0ng-Pickle-Pass!', role='user',
        )
        self.other = User.objects.create_user(
            username='other', password='Str0ng-Pickle-Pass!', role='user',
        )
        site = Site.objects.create(name='Main Site')
        self.court = Court.objects.create(
            name='Court 1', site=site, hourly_rate=500, is_active=True,
        )
        self.date = timezone.localdate() + timedelta(days=3)

    def book(self, start, end, user=None):
        return Reservation.objects.create(
            user=user or self.other, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat(start),
            end_time=dt_time.fromisoformat(end),
            duration_hours=2, hourly_rate=500, subtotal=1000, total_amount=1000,
            status='confirmed',
        )

    def slots(self, start='09:00', end='11:00'):
        return dt_time.fromisoformat(start), dt_time.fromisoformat(end)


class JoinWaitlistTests(WaitlistServiceTestCase):
    def test_join_is_rejected_when_the_slot_is_still_free(self):
        start, end = self.slots()

        with self.assertRaises(WaitlistError):
            join_waitlist(
                user=self.user, court=self.court, date=self.date,
                start_time=start, end_time=end,
            )

    def test_join_creates_an_entry_when_the_slot_is_booked(self):
        self.book('09:00', '11:00')
        start, end = self.slots()

        entry, created = join_waitlist(
            user=self.user, court=self.court, date=self.date,
            start_time=start, end_time=end,
        )

        self.assertTrue(created)
        self.assertEqual(entry.status, 'waiting')
        self.assertEqual(WaitlistEntry.objects.count(), 1)

    def test_ducplicate_join_returns_the_existing_entry(self):
        self.book('09:00', '11:00')
        start, end = self.slots()
        join_waitlist(
            user=self.user, court=self.court, date=self.date,
            start_time=start, end_time=end,
        )

        entry, created = join_waitlist(
            user=self.user, court=self.court, date=self.date,
            start_time=start, end_time=end,
        )

        self.assertFalse(created)
        self.assertEqual(WaitlistEntry.objects.count(), 1)

    def test_join_rejects_a_past_slot(self):
        past = timezone.localdate() - timedelta(days=1)
        start, end = self.slots()

        with self.assertRaises(WaitlistError):
            join_waitlist(
                user=self.user, court=self.court, date=past,
                start_time=start, end_time=end,
            )


class WaitlistNotifyTests(WaitlistServiceTestCase):
    def test_releasing_a_slot_notifies_the_next_person(self):
        held = self.book('09:00', '11:00')
        start, end = self.slots()
        entry, _ = join_waitlist(
            user=self.user, court=self.court, date=self.date,
            start_time=start, end_time=end,
        )

        release_slot_and_notify_waitlist(held)

        entry.refresh_from_db()
        self.assertEqual(entry.status, 'notified')
        self.assertIsNotNone(entry.notified_at)
        self.assertTrue(Notification.objects.filter(
            user=self.user, title='Slot Available!',
        ).exists())

    def test_release_with_no_waiters_is_a_noop(self):
        held = self.book('09:00', '11:00')

        self.assertIsNone(release_slot_and_notify_waitlist(held))

    def test_booking_the_slot_marks_the_entry_claimed(self):
        WaitlistEntry.objects.create(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat('09:00'),
            end_time=dt_time.fromisoformat('11:00'),
            status='waiting',
        )

        create_reservation_atomic(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time.fromisoformat('09:00'),
            end_time=dt_time.fromisoformat('11:00'),
            checkout_data={'duration_hours': 2.0},
        )

        entry = WaitlistEntry.objects.get()
        self.assertEqual(entry.status, 'claimed')
        self.assertIsNotNone(entry.claimed_at)


class WaitlistViewTests(WaitlistServiceTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_join_requires_post(self):
        response = self.client.get(
            reverse('waitlist_join', args=[self.court.id]),
        )

        self.assertEqual(response.status_code, 302)

    def test_join_view_creates_an_entry_and_redirects_to_the_list(self):
        self.book('09:00', '11:00')

        response = self.client.post(
            reverse('waitlist_join', args=[self.court.id]),
            {'date': self.date.isoformat(), 'start': '09:00', 'end': '11:00'},
        )

        self.assertRedirects(response, reverse('waitlist_list'))
        self.assertEqual(WaitlistEntry.objects.filter(user=self.user).count(), 1)

    def test_list_only_shows_the_users_own_entries(self):
        WaitlistEntry.objects.create(
            user=self.other, court=self.court, date=self.date,
            start_time=dt_time(9, 0), end_time=dt_time(11, 0),
        )
        mine = WaitlistEntry.objects.create(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time(11, 0), end_time=dt_time(13, 0),
        )

        response = self.client.get(reverse('waitlist_list'))

        entries = list(response.context['entries'])
        self.assertEqual([e.id for e in entries], [mine.id])

    def test_leave_view_cancels_the_entry(self):
        entry = WaitlistEntry.objects.create(
            user=self.user, court=self.court, date=self.date,
            start_time=dt_time(9, 0), end_time=dt_time(11, 0),
            status='waiting',
        )

        response = self.client.post(reverse('waitlist_leave', args=[entry.id]))

        self.assertRedirects(response, reverse('waitlist_list'))
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'cancelled')

    def test_leave_view_cannot_touch_someone_elses_entry(self):
        entry = WaitlistEntry.objects.create(
            user=self.other, court=self.court, date=self.date,
            start_time=dt_time(9, 0), end_time=dt_time(11, 0),
        )

        response = self.client.post(reverse('waitlist_leave', args=[entry.id]))

        self.assertEqual(response.status_code, 404)
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'waiting')
