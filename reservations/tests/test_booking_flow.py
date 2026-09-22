"""View tests for the reservation booking flow.

Booking is the app's primary transaction: a user picks a court and a time slot,
the slot is re-verified server-side, the request is stashed in the session and
the user is sent to checkout. These tests pin that contract so extracting
pricing/availability logic into services cannot change it silently.
"""

from datetime import time as dt_time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from equipment.models import Equipment
from reservations.models import Reservation

# PBKDF2 (the default hasher) costs roughly a second per user and dominates the
# runtime of this module; the booking flow does not care which hasher is used.
FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class BookingFlowTestCase(TestCase):
    """Shared fixtures for the booking-flow view tests."""

    password = 'Str0ng-Pickle-Pass!'

    def setUp(self):
        self.user = User.objects.create_user(
            username='booker', password=self.password, role='user',
        )
        self.staff = User.objects.create_user(
            username='staffuser', password=self.password, role='staff',
        )
        self.site = Site.objects.create(name='1st Floor')
        self.court = Court.objects.create(
            name='Court 1', site=self.site, hourly_rate=500, is_active=True,
        )
        self.client.force_login(self.user)

    def future_date(self, days=3):
        return (timezone.localdate() + timedelta(days=days)).isoformat()

    def booking_payload(self, **overrides):
        payload = {
            'court': self.court.id,
            'date': self.future_date(),
            'time_slot': '09:00-11:00',
            'notes': 'Bringing own paddle',
            'match_name': 'Morning match',
            'match_format': 'singles',
            'game_type': 'friendly',
            'scoring_format': '11',
            'points_per_game': 11,
            'games_to_win': 2,
            'win_by_two': 'on',
        }
        payload.update(overrides)
        return payload

    def existing_reservation(self, start, end, status='confirmed', user=None):
        # TimeField values must be real time objects: Reservation.save() calls
        # datetime.combine() on them before the field has a chance to coerce a
        # string.
        return Reservation.objects.create(
            user=user or self.user,
            court=self.court,
            date=timezone.localdate() + timedelta(days=3),
            start_time=dt_time.fromisoformat(start),
            end_time=dt_time.fromisoformat(end),
            duration_hours=2,
            hourly_rate=500,
            subtotal=1000,
            total_amount=1000,
            status=status,
        )


class ReservationCreateViewTests(BookingFlowTestCase):
    def test_get_renders_the_booking_form(self):
        response = self.client.get(reverse('reservation_create'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/reservations/reservation_create.html')
        self.assertIn('form', response.context)

    def test_anonymous_visitor_is_sent_to_login(self):
        self.client.logout()

        response = self.client.get(reverse('reservation_create'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_staff_user_is_redirected_away_from_the_user_booking_page(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('reservation_create'))

        self.assertEqual(response.status_code, 302)

    def test_valid_post_stashes_checkout_data_in_the_session(self):
        response = self.client.post(reverse('reservation_create'), data=self.booking_payload())

        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/checkout/', response['Location'])

        checkout_data = self.client.session['checkout_data']
        self.assertEqual(checkout_data['court_id'], self.court.id)
        self.assertEqual(checkout_data['date'], self.future_date())
        self.assertEqual(checkout_data['start_time'], '09:00')
        self.assertEqual(checkout_data['end_time'], '11:00')
        self.assertEqual(checkout_data['duration_hours'], 2.0)
        self.assertEqual(checkout_data['hourly_rate'], 500.0)
        self.assertEqual(checkout_data['subtotal'], 1000.0)

    def test_valid_post_does_not_create_a_reservation_before_payment(self):
        # The reservation is deliberately deferred until the payment step; a
        # regression here would create ghost reservations for abandoned carts.
        self.client.post(reverse('reservation_create'), data=self.booking_payload())

        self.assertEqual(Reservation.objects.count(), 0)

    def test_selected_equipment_ids_are_carried_into_the_checkout_session(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Starter Paddle', rental_price=50, quantity_available=3,
        )

        self.client.post(
            reverse('reservation_create'),
            data=self.booking_payload(**{'equipment': [str(paddle.id)]}),
        )

        self.assertEqual(self.client.session['checkout_data']['equipment_ids'], [paddle.id])

    def test_expired_slot_is_rejected_before_the_session_is_written(self):
        past_date = (timezone.localdate() - timedelta(days=1)).isoformat()

        response = self.client.post(
            reverse('reservation_create'), data=self.booking_payload(date=past_date),
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('checkout_data', self.client.session)

    def test_double_booked_slot_is_rejected_on_the_server(self):
        self.existing_reservation('10:00', '12:00')

        response = self.client.post(reverse('reservation_create'), data=self.booking_payload())

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('checkout_data', self.client.session)
        messages = [str(m) for m in response.context['messages']]
        # The form layer reports the clash as "not available"; the view's
        # "just booked" variant only fires on a genuine race after validation.
        self.assertTrue(any(
            'not available for the selected time slot' in m
            or 'time slot was just booked' in m
            for m in messages
        ), f'actual messages: {messages}')

    def test_adjacent_slot_is_still_bookable(self):
        # 09:00-11:00 must stay free when 11:00-13:00 exists: the overlap test
        # has to exclude ranges that merely touch.
        self.existing_reservation('11:00', '13:00')

        response = self.client.post(reverse('reservation_create'), data=self.booking_payload())

        self.assertEqual(response.status_code, 302)

    def test_cancelled_reservation_does_not_block_the_slot(self):
        self.existing_reservation('10:00', '12:00', status='cancelled')

        response = self.client.post(reverse('reservation_create'), data=self.booking_payload())

        self.assertEqual(response.status_code, 302)


class ReservationListAndDetailViewTests(BookingFlowTestCase):
    def setUp(self):
        super().setUp()
        self.mine = self.existing_reservation('08:00', '10:00')
        other = User.objects.create_user(username='other', password=self.password)
        self.theirs = self.existing_reservation('10:00', '12:00', user=other)

    def test_list_only_shows_the_signed_in_users_reservations(self):
        response = self.client.get(reverse('reservation_list'))

        self.assertEqual(response.status_code, 200)
        reservation_ids = [r.id for r in response.context['page_obj'].object_list]
        self.assertIn(self.mine.id, reservation_ids)
        self.assertNotIn(self.theirs.id, reservation_ids)

    def test_list_status_filter_is_applied(self):
        Reservation.objects.filter(pk=self.mine.pk).update(status='cancelled')

        response = self.client.get(reverse('reservation_list'), {'status': 'cancelled'})

        reservation_ids = [r.id for r in response.context['page_obj'].object_list]
        self.assertEqual(reservation_ids, [self.mine.id])

    def test_owner_can_open_the_detail_page(self):
        response = self.client.get(reverse('reservation_detail', args=[self.mine.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/reservations/reservation_detail.html')

    def test_other_user_cannot_open_someone_elses_reservation(self):
        response = self.client.get(
            reverse('reservation_detail', args=[self.theirs.id]), follow=True,
        )

        self.assertRedirects(response, reverse('reservation_list'))

    def test_staff_can_open_a_users_reservation(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('reservation_detail', args=[self.mine.id]))

        self.assertEqual(response.status_code, 200)


class ReservationDetailWindowTests(BookingFlowTestCase):
    def test_editing_window_is_open_right_after_creation(self):
        reservation = self.existing_reservation('08:00', '10:00', status='pending')

        response = self.client.get(reverse('reservation_detail', args=[reservation.id]))

        self.assertTrue(response.context['can_edit'])

    def test_editing_window_closes_once_the_policy_limit_has_passed(self):
        reservation = self.existing_reservation('08:00', '10:00', status='pending')
        Reservation.objects.filter(pk=reservation.pk).update(
            created_at=timezone.now() - timedelta(hours=5),
        )

        response = self.client.get(reverse('reservation_detail', args=[reservation.id]))

        self.assertFalse(response.context['can_edit'])

    def test_expired_redirect_notice_is_shown(self):
        reservation = self.existing_reservation('08:00', '10:00', status='pending')

        response = self.client.get(
            reverse('reservation_detail', args=[reservation.id]), {'expired': '1'},
        )

        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('editing window has expired' in m for m in messages))


class SlotVerificationApiTests(BookingFlowTestCase):
    """The booking page calls these endpoints before the form is submitted."""

    def test_time_slots_api_requires_court_and_date(self):
        response = self.client.get(reverse('get_time_slots'))

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_time_slots_api_marks_a_booked_hour_as_unavailable(self):
        self.existing_reservation('10:00', '11:00')

        response = self.client.get(reverse('get_time_slots'), {
            'court_id': self.court.id, 'date': self.future_date(),
        })

        self.assertEqual(response.status_code, 200)
        slots = {slot['start']: slot for slot in response.json()['slots']}
        self.assertFalse(slots['10:00']['available'])

    def test_verify_slot_api_reports_a_free_slot_as_available(self):
        response = self.client.get(reverse('verify_slot'), {
            'court_id': self.court.id, 'date': self.future_date(),
            'start': '09:00', 'end': '11:00',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['available'])

    def test_verify_slot_api_reports_an_overlapping_slot_as_taken(self):
        self.existing_reservation('10:00', '12:00')

        response = self.client.get(reverse('verify_slot'), {
            'court_id': self.court.id, 'date': self.future_date(),
            'start': '09:00', 'end': '11:00',
        })

        self.assertFalse(response.json()['available'])

    def test_verify_slot_api_rejects_a_slot_in_the_past(self):
        response = self.client.get(reverse('verify_slot'), {
            'court_id': self.court.id,
            'date': (timezone.localdate() - timedelta(days=1)).isoformat(),
            'start': '09:00', 'end': '11:00',
        })

        self.assertFalse(response.json()['available'])
        self.assertIn('passed', response.json()['message'])

    def test_monthly_availability_api_classifies_every_day_of_the_month(self):
        self.existing_reservation('08:00', '09:00')
        today = timezone.localdate()

        response = self.client.get(reverse('get_monthly_availability'), {
            'court_id': self.court.id, 'year': today.year, 'month': today.month,
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['month'], today.month)
        self.assertIn(today.isoformat(), payload['availability'])
        # Days before today are marked 'past' so the calendar can grey them out;
        # today itself must never be reported as past.
        self.assertNotEqual(payload['availability'][today.isoformat()], 'past')
        future_day = (today + timedelta(days=1)).isoformat()
        if future_day in payload['availability']:
            self.assertIn(payload['availability'][future_day], ('available', 'full'))
