"""
Stripe Webhook Handler for PickleSphere

Processes incoming Stripe webhook events:
- checkout.session.completed
- payment_intent.succeeded
- payment_intent.payment_failed
- charge.refunded

All webhook endpoints are CSRF-exempt and require signature verification.

Idempotency: Stripe delivers events at least once and retries non-2xx
responses. Every event is recorded in ``StripeWebhookEvent`` before it is
handled. A duplicate delivery is acknowledged (200) without re-processing. If a
handler fails, the marker is removed and a 500 is returned so Stripe retries.
"""

import logging

from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import StripeWebhookEvent
from .stripe_integration import (
    process_stripe_webhook,
    handle_checkout_session_completed,
    handle_payment_intent_succeeded,
    handle_payment_intent_payment_failed,
    handle_charge_refunded,
)

logger = logging.getLogger(__name__)


def _event_id(event):
    """Extract the Stripe event id from a dict or a Stripe object."""
    if event is None:
        return None
    if isinstance(event, dict):
        return event.get('id')
    return getattr(event, 'id', None)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Main Stripe webhook endpoint.
    Receives events from Stripe and processes them accordingly.

    URL: /payments/stripe/webhook/
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not sig_header:
        logger.warning("Stripe webhook received without signature header")
        return HttpResponse(status=400)

    event_type, event = process_stripe_webhook(payload, sig_header)

    if event_type is None:
        logger.error("Stripe webhook processing failed - invalid signature or payload")
        return HttpResponse(status=400)

    event_id = _event_id(event)

    # Record the event before handling it. ``created`` is False on a duplicate
    # delivery, in which case we acknowledge without re-processing.
    if event_id:
        try:
            _, created = StripeWebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={'event_type': event_type},
            )
        except Exception:
            logger.exception("Failed to record Stripe webhook event %s", event_id)
            return HttpResponse(status=500)
        if not created:
            logger.info("Stripe webhook %s already processed; skipping", event_id)
            return HttpResponse(status=200)
    else:
        created = None
        logger.warning("Stripe webhook %s has no event id; cannot deduplicate", event_type)

    try:
        success = _dispatch(event_type, event)
        if not success:
            raise RuntimeError(f'Handler for {event_type} reported failure')
        logger.info("Stripe webhook %s processed", event_type)
        return HttpResponse(status=200)

    except Exception as exc:
        # Remove the marker so Stripe's retry can process this event again.
        if event_id and created:
            StripeWebhookEvent.objects.filter(event_id=event_id).delete()
        logger.error(
            "Error processing Stripe webhook event %s: %s", event_type, exc,
            exc_info=True,
        )
        return HttpResponse(status=500)


@transaction.atomic
def _dispatch(event_type, event):
    """Run the handler for a verified, non-duplicate event.

    Returns True when the event was handled (or intentionally ignored).
    Unhandled event types are acknowledged so Stripe stops retrying them.
    """
    if event_type == 'checkout.session.completed':
        return handle_checkout_session_completed(event['data']['object'])

    if event_type == 'payment_intent.succeeded':
        return handle_payment_intent_succeeded(event['data']['object'])

    if event_type == 'payment_intent.payment_failed':
        handle_payment_intent_payment_failed(event['data']['object'])
        return True

    if event_type == 'charge.refunded':
        return handle_charge_refunded(event['data']['object'])

    if event_type == 'checkout.session.expired':
        return _handle_checkout_session_expired(event['data']['object'])

    logger.debug("Unhandled Stripe webhook event type: %s", event_type)
    return True


def _handle_checkout_session_expired(session):
    """Fail the pending payment and release the reservation it held."""
    from .models import Payment

    payment_id = (session.get('metadata') or {}).get('payment_id')
    if not payment_id:
        return True

    try:
        payment = Payment.objects.select_related('reservation').get(id=payment_id)
    except Payment.DoesNotExist:
        logger.warning("Payment #%s not found for expired session cleanup", payment_id)
        return True

    if payment.status == 'pending':
        payment.status = 'failed'
        payment.payment_notes = 'Stripe checkout session expired'
        payment.save(update_fields=['status', 'payment_notes'])
        reservation = payment.reservation
        if reservation.status == 'pending':
            reservation.status = 'cancelled'
            reservation.save(update_fields=['status'])
            from reservations.services import release_slot_and_notify_waitlist
            release_slot_and_notify_waitlist(reservation)
        logger.info(
            "Payment #%s and reservation #%s cancelled due to expired Stripe session",
            payment.id, reservation.id,
        )
    return True
