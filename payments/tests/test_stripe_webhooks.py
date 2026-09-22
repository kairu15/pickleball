"""Tests for the Stripe webhook endpoint and its handlers.

Webhooks are how money actually lands: a forged request must never be able to
confirm a payment (signature check), and a legitimate replay must not
double-process one (idempotency). Real Stripe networking is avoided by patching
``process_stripe_webhook`` and by passing Stripe-shaped dicts straight to the
handlers in ``stripe_integration.py`` — those handlers are also what the
upcoming payments refactor will move into a service module, so the money
behaviour itself is exercised directly.
"""

from datetime import date, time as dt_time

from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from accounts.models import User
from courts.models import Court, Site
from notifications.models import Notification
from payments.models import Payment, PaymentLog
from reservations.models import Reservation

FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


def make_pending_booking(username, court_name, start, end, duration, subtotal):
    """A pending reservation + pending payment, as checkout would have left them."""
    user = User.objects.create_user(
        username=username, password='Str0ng-Pickle-Pass!', role='user',
    )
    site = Site.objects.create(name=f'{court_name} Site')
    court = Court.objects.create(
        name=court_name, site=site, hourly_rate=500, is_active=True,
    )
    reservation = Reservation.objects.create(
        user=user, court=court, date=date(2030, 1, 1),
        start_time=start, end_time=end, duration_hours=duration,
        hourly_rate=500, subtotal=subtotal, total_amount=subtotal,
        status='pending',
    )
    payment = Payment.objects.create(
        reservation=reservation, amount=subtotal, status='pending',
    )
    return user, reservation, payment


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class StripeWebhookEndpointTests(TestCase):
    def setUp(self):
        _, self.reservation, self.payment = make_pending_booking(
            'webhookuser', 'Court W', dt_time(9, 0), dt_time(11, 0), 2, 1000,
        )
        self.url = reverse('stripe_webhook')

    def post_event(self, payload=b'{}', signature='t=1,v1=bogus'):
        return self.client.post(
            self.url, data=payload, content_type='application/json',
            HTTP_STRIPE_SIGNATURE=signature,
        )

    def test_missing_signature_header_is_rejected(self):
        response = self.client.post(self.url, data=b'{}', content_type='application/json')

        self.assertEqual(response.status_code, 400)

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_invalid_signature_is_rejected(self):
        with patch('payments.webhooks.process_stripe_webhook', return_value=(None, None)):
            response = self.post_event()

        self.assertEqual(response.status_code, 400)

    def test_unhandled_event_type_is_acknowledged(self):
        event = ('customer.created', {'id': 'evt_1'})
        with patch('payments.webhooks.process_stripe_webhook', return_value=event):
            response = self.post_event()

        self.assertEqual(response.status_code, 200)

    def test_handler_failure_returns_500_so_stripe_retries(self):
        event = ('checkout.session.completed', {'data': {'object': {'id': 'cs_1'}}})
        with patch('payments.webhooks.process_stripe_webhook', return_value=event), \
                patch(
                    'payments.webhooks.handle_checkout_session_completed',
                    return_value=False,
                ):
            response = self.post_event()

        self.assertEqual(response.status_code, 500)

    def test_expired_checkout_session_cancels_the_pending_hold(self):
        event = ('checkout.session.expired', {'data': {'object': {
            'id': 'cs_expired', 'metadata': {'payment_id': str(self.payment.id)},
        }}})

        with patch('payments.webhooks.process_stripe_webhook', return_value=event):
            response = self.post_event()

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')
        self.assertEqual(self.reservation.status, 'cancelled')

    def test_expired_session_without_a_matching_payment_is_ignored(self):
        event = ('checkout.session.expired', {'data': {'object': {
            'id': 'cs_gone', 'metadata': {'payment_id': '999999'},
        }}})

        with patch('payments.webhooks.process_stripe_webhook', return_value=event):
            response = self.post_event()

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')


class HandleCheckoutSessionCompletedTests(TestCase):
    """Exercise the handler itself with Stripe-shaped data (no network)."""

    def setUp(self):
        self.user, self.reservation, self.payment = make_pending_booking(
            'stripeuser', 'Court S', dt_time(9, 0), dt_time(11, 0), 2, 1000,
        )
        self.session = {
            'id': 'cs_test_123',
            'payment_intent': 'pi_test_456',
            'metadata': {'payment_id': str(self.payment.id)},
        }

    def test_completed_session_pays_the_payment_and_confirms_the_reservation(self):
        from payments.stripe_integration import handle_checkout_session_completed

        success = handle_checkout_session_completed(self.session)

        self.assertTrue(success)
        self.payment.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        self.assertEqual(self.payment.stripe_payment_intent_id, 'pi_test_456')
        self.assertEqual(self.payment.transaction_id, 'PI_TEST_')  # first 8 chars, upper
        self.assertEqual(self.reservation.status, 'confirmed')
        self.assertTrue(
            PaymentLog.objects.filter(
                payment=self.payment, action='Stripe Payment Completed',
            ).exists()
        )

    def test_completion_notifies_the_booker(self):
        from payments.stripe_integration import handle_checkout_session_completed

        handle_checkout_session_completed(self.session)

        self.assertTrue(
            Notification.objects.filter(user=self.user, category='payment').exists()
        )

    def test_session_without_a_payment_id_fails_without_touching_data(self):
        from payments.stripe_integration import handle_checkout_session_completed

        success = handle_checkout_session_completed({'id': 'cs_nometa', 'metadata': {}})

        self.assertFalse(success)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')
        self.assertEqual(self.reservation.status, 'pending')


class HandlePaymentIntentTests(TestCase):
    """payment_intent.succeeded / payment_failed handlers."""

    def setUp(self):
        self.user, self.reservation, self.payment = make_pending_booking(
            'intentuser', 'Court I', dt_time(13, 0), dt_time(14, 0), 1, 500,
        )

    def intent(self, **overrides):
        payload = {
            'id': 'pi_test_789',
            'metadata': {'payment_id': str(self.payment.id)},
            'charges': {'data': [{
                'receipt_url': 'https://pay.stripe.com/receipts/r1',
                'payment_method_details': {'type': 'card'},
            }]},
        }
        payload.update(overrides)
        return payload

    def test_succeeded_intent_marks_the_payment_paid_and_confirms(self):
        from payments.stripe_integration import handle_payment_intent_succeeded

        success = handle_payment_intent_succeeded(self.intent())

        self.assertTrue(success)
        self.payment.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        self.assertEqual(self.payment.stripe_receipt_url, 'https://pay.stripe.com/receipts/r1')
        self.assertEqual(self.reservation.status, 'confirmed')

    def test_succeeded_intent_is_idempotent_on_replay(self):
        from payments.stripe_integration import handle_payment_intent_succeeded

        self.assertTrue(handle_payment_intent_succeeded(self.intent()))
        log_count = PaymentLog.objects.count()

        success = handle_payment_intent_succeeded(self.intent())

        self.assertTrue(success)  # acknowledged, not an error
        self.assertEqual(PaymentLog.objects.count(), log_count)

    def test_succeeded_intent_without_a_matching_payment_is_a_clean_no_op(self):
        from payments.stripe_integration import handle_payment_intent_succeeded

        success = handle_payment_intent_succeeded(
            self.intent(metadata={'payment_id': '424242'})
        )

        self.assertFalse(success)

    def test_failed_intent_marks_the_payment_failed_and_leaves_the_reservation(self):
        from payments.stripe_integration import handle_payment_intent_payment_failed

        result = handle_payment_intent_payment_failed(self.intent(
            last_payment_error={'message': 'Your card was declined.'},
        ))

        self.assertTrue(result)
        self.payment.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')
        self.assertIn('declined', self.payment.payment_notes)
        self.assertEqual(self.reservation.status, 'pending')
        self.assertTrue(PaymentLog.objects.filter(action='Stripe Payment Failed').exists())
