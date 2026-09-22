"""View tests for the payment checkout flow.

The session-based checkout in ``payments/views.py`` is the money path: it
creates the reservation, attaches equipment, creates the payment, notifies staff
and clears the session. It is also the biggest function in the project, so these
tests exist to keep the behaviour identical while it is split into service
modules.

All Stripe calls are avoided: the ``stripe`` branch and the webhook signature
check are covered separately in ``test_stripe_webhooks.py``.
"""

from datetime import time as dt_time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from courts.models import Court, Site
from equipment.models import Equipment
from notifications.models import Notification
from payments.models import Payment, PaymentLog, PaymentSettings
from reservations.models import Reservation, ReservationEquipment

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# The checkout URL is keyed by a UUID-shaped token (see payments/user_urls.py);
# any valid UUID works because the view only guards the session payload.
CHECKOUT_TOKEN = 'abcd1234-5678-9abc-def0-1234567890ab'



def checkout_data(court, **overrides):
    """A ``checkout_data`` session payload as written by reservation_create_view."""
    payload = {
        'court_id': court.id,
        'date': (timezone.localdate() + timedelta(days=2)).isoformat(),
        'start_time': '09:00',
        'end_time': '11:00',
        'duration_hours': 2.0,
        'hourly_rate': 500.0,
        'subtotal': 1000.0,
        'notes': 'Bringing own paddle',
        'equipment_ids': [],
        'match_name': 'Morning match',
        'match_format': 'singles',
        'game_type': 'friendly',
        'scoring_format': '11',
        'points_per_game': 11,
        'games_to_win': 2,
        'win_by_two': True,
        'team1_player2_id': None,
        'team2_player1_id': None,
        'team2_player2_id': None,
        'team1_name': '',
        'team2_name': '',
        'guest_players_data': None,
        'guest_team1_p2': '',
        'guest_team2_p1': '',
        'guest_team2_p2': '',
    }
    payload.update(overrides)
    return payload


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class CheckoutFlowTestCase(TestCase):
    password = 'Str0ng-Pickle-Pass!'

    def setUp(self):
        self.user = User.objects.create_user(
            username='payer', password=self.password, role='user',
        )
        self.staff = User.objects.create_user(
            username='staffpayer', password=self.password, role='staff',
        )
        self.site = Site.objects.create(name='Main Site')
        self.court = Court.objects.create(
            name='Court A', site=self.site, hourly_rate=500, is_active=True,
        )
        self.client.force_login(self.user)

    def start_checkout(self, **overrides):
        """Put a checkout payload in the session the way the booking view does."""
        session = self.client.session
        session['checkout_data'] = checkout_data(self.court, **overrides)
        session.save()

    def enable_online_payments(self, methods=('gcash',)):
        return PaymentSettings.objects.create(
            gcash_number='09171234567' if 'gcash' in methods else None,
            gcash_account_name='PickleSphere' if 'gcash' in methods else None,
            accepted_payment_methods=list(methods),
            is_active=True,
        )

    def existing_reservation(self, start, end, status='confirmed'):
        # Reservation.save() calls datetime.combine() with these values, so they
        # must be time objects rather than the strings the DB layer accepts.
        return Reservation.objects.create(
            user=self.user, court=self.court,
            date=timezone.localdate() + timedelta(days=2),
            start_time=dt_time.fromisoformat(start), end_time=dt_time.fromisoformat(end),
            duration_hours=2, hourly_rate=500, subtotal=1000, total_amount=1000,
            status=status,
        )


class CheckoutPageTests(CheckoutFlowTestCase):
    def test_get_renders_the_checkout_page_from_the_session(self):
        self.start_checkout()

        response = self.client.get(reverse('checkout_page', args=[CHECKOUT_TOKEN]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/payments/checkout.html')
        self.assertEqual(response.context['total_amount'], 1000.0)
        self.assertTrue(response.context['is_session_checkout'])

    def test_expired_session_sends_the_user_back_to_booking(self):
        response = self.client.get(reverse('checkout_page', args=[CHECKOUT_TOKEN]))

        self.assertRedirects(response, reverse('reservation_create'))

    def test_equipment_in_the_session_is_added_to_the_total(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Pro Paddle', rental_price=75, quantity_available=2,
        )
        self.start_checkout(equipment_ids=[paddle.id])

        response = self.client.get(reverse('checkout_page', args=[CHECKOUT_TOKEN]))

        self.assertEqual(response.context['total_equipment_fee'], 75.0)
        self.assertEqual(response.context['total_amount'], 1075.0)

    def test_anonymous_visitor_cannot_open_the_checkout_page(self):
        self.client.logout()

        response = self.client.get(reverse('checkout_page', args=[CHECKOUT_TOKEN]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


class CashPaymentTests(CheckoutFlowTestCase):
    def test_cash_submission_creates_a_pending_reservation_and_payment(self):
        self.start_checkout()

        response = self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]),
            {'method': 'cash', 'payment_notes': 'Will pay at the counter'},
        )

        reservation = Reservation.objects.get()
        payment = Payment.objects.get()
        self.assertRedirects(response, reverse('payment_status', args=[payment.id]))
        self.assertEqual(reservation.status, 'pending')
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.court, self.court)
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.method, 'cash')
        self.assertEqual(float(payment.amount), 1000.0)
        self.assertTrue(PaymentLog.objects.filter(payment=payment).exists())

    def test_session_is_cleared_after_a_successful_submission(self):
        self.start_checkout()

        self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]),
            {'method': 'cash', 'payment_notes': ''},
        )

        self.assertNotIn('checkout_data', self.client.session)

    def test_staff_are_notified_about_the_new_pending_payment(self):
        self.start_checkout()

        self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]),
            {'method': 'cash', 'payment_notes': ''},
        )

        self.assertTrue(Notification.objects.filter(user=self.staff).exists())

    def test_cash_submission_attaches_equipment_and_adds_the_rental_fee(self):
        paddle = Equipment.objects.create(
            type='paddle', name='Rental Paddle', rental_price=50,
            quantity_total=2, quantity_available=2,
        )
        self.start_checkout(equipment_ids=[paddle.id])

        self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]),
            {'method': 'cash', 'payment_notes': ''},
        )

        reservation = Reservation.objects.get()
        self.assertEqual(
            ReservationEquipment.objects.filter(reservation=reservation).count(), 1,
        )
        self.assertEqual(float(reservation.equipment_fee), 50.0)
        self.assertEqual(float(reservation.total_amount), 1050.0)

        paddle.refresh_from_db()
        self.assertEqual(paddle.quantity_available, 1)

    def test_slot_taken_while_on_the_checkout_page_is_rejected(self):
        self.start_checkout()
        self.existing_reservation('10:00', '12:00')

        response = self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]),
            {'method': 'cash', 'payment_notes': ''},
        )

        # The view re-verifies availability before creating anything and
        # bounces the user back to the booking form.
        self.assertRedirects(response, reverse('reservation_create'))
        self.assertEqual(Reservation.objects.count(), 1)  # only the pre-existing one
        self.assertEqual(Payment.objects.count(), 0)

    def test_unknown_payment_method_is_rejected(self):
        self.start_checkout()

        response = self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]), {'method': 'bitcoin'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)


class OnlinePaymentTests(CheckoutFlowTestCase):
    """GCash / Maya / bank transfer all go through the same verification path."""

    def test_gcash_submission_records_the_reference_and_awaits_verification(self):
        self.enable_online_payments()
        self.start_checkout()

        response = self.client.post(reverse('checkout_page', args=[CHECKOUT_TOKEN]), {
            'method': 'gcash',
            'gcash_reference': 'REF-123456',
        })

        payment = Payment.objects.get()
        self.assertRedirects(response, reverse('payment_status', args=[payment.id]))
        self.assertEqual(payment.method, 'gcash')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.gcash_reference, 'REF-123456')
        self.assertNotIn('checkout_data', self.client.session)

    def test_online_method_is_blocked_when_the_settings_are_missing(self):
        self.start_checkout()

        response = self.client.post(reverse('checkout_page', args=[CHECKOUT_TOKEN]), {
            'method': 'gcash',
            'gcash_reference': 'REF-123456',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertContains(response, 'Online payment is not available yet')

    def test_online_method_is_blocked_when_the_admin_disabled_it(self):
        PaymentSettings.objects.create(
            gcash_number='09170000000', gcash_account_name='PickleSphere',
            accepted_payment_methods=['gcash'], is_active=False,
        )
        self.start_checkout()

        self.client.post(reverse('checkout_page', args=[CHECKOUT_TOKEN]), {
            'method': 'gcash', 'gcash_reference': 'REF-123456',
        })

        self.assertEqual(Reservation.objects.count(), 0)

    def test_gcash_reference_is_optional_at_submission_time(self):
        self.enable_online_payments()
        self.start_checkout()

        response = self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]), {'method': 'gcash'},
        )

        # The reference/proof is uploaded later; rejecting here would throw
        # away the whole checkout, so the pending payment is still created.
        payment = Payment.objects.get()
        self.assertRedirects(response, reverse('payment_status', args=[payment.id]))
        self.assertEqual(payment.status, 'pending')
        self.assertFalse(payment.gcash_reference)


class CardPaymentTests(CheckoutFlowTestCase):
    """The in-app card path marks the payment paid and confirms the reservation."""

    def test_card_payment_confirms_the_reservation_immediately(self):
        self.start_checkout()

        response = self.client.post(
            reverse('checkout_page', args=[CHECKOUT_TOKEN]), {'method': 'card'},
        )

        reservation = Reservation.objects.get()
        payment = Payment.objects.get()
        self.assertRedirects(response, reverse('reservation_detail', args=[reservation.id]))
        self.assertEqual(reservation.status, 'confirmed')
        self.assertEqual(payment.status, 'paid')
        self.assertEqual(payment.method, 'card')
        self.assertTrue(payment.transaction_id)

    def test_card_payment_is_logged_against_the_paying_user(self):
        self.start_checkout()

        self.client.post(reverse('checkout_page', args=[CHECKOUT_TOKEN]), {'method': 'card'})

        log = PaymentLog.objects.get()
        self.assertEqual(log.action, 'Card Payment Processed')
        self.assertEqual(log.performed_by, self.user)


class PaymentStatusViewTests(CheckoutFlowTestCase):
    def setUp(self):
        super().setUp()
        self.reservation = self.existing_reservation('09:00', '11:00')
        self.payment = Payment.objects.create(
            reservation=self.reservation, amount=1000, status='pending', method='cash',
        )

    def test_owner_can_view_the_payment_status_page(self):
        response = self.client.get(reverse('payment_status', args=[self.payment.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/payments/payment_status.html')
        self.assertEqual(response.context['payment'], self.payment)

    def test_other_users_cannot_view_someone_elses_payment(self):
        intruder = User.objects.create_user(username='intruder', password=self.password)
        self.client.force_login(intruder)

        response = self.client.get(
            reverse('payment_status', args=[self.payment.id]), follow=True,
        )

        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('do not have permission' in m for m in messages))

    def test_staff_can_view_any_payment(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('payment_status', args=[self.payment.id]))

        self.assertEqual(response.status_code, 200)
