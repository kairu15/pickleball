"""
Stripe Integration Module for PickleSphere

Handles:
- Creating PaymentIntents for card payments
- Creating Checkout Sessions (GCash, cards, grabpay)
- Webhook event processing
- Refund processing via Stripe

Environment variables needed:
- STRIPE_SECRET_KEY
- STRIPE_PUBLISHABLE_KEY (for templates)
- STRIPE_WEBHOOK_SECRET (for webhook signature verification)
"""

import stripe
import logging
from datetime import timedelta
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(payment, success_url, cancel_url):
    """
    Create a Stripe Checkout Session for a payment.
    
    Supports:
    - Card payments (default)
    - GCash (if enabled on Stripe account)
    - GrabPay (if enabled on Stripe account)
    
    Returns the checkout session object or None on error.
    """
    try:
        # Build line items from the reservation
        reservation = payment.reservation
        court = reservation.court
        
        line_items = [
            {
                'price_data': {
                    'currency': 'php',
                    'product_data': {
                        'name': f'Court Rental: {court.name}',
                        'description': (
                            f'{reservation.date.strftime("%b %d, %Y")} '
                            f'{reservation.start_time.strftime("%I:%M %p")} - '
                            f'{reservation.end_time.strftime("%I:%M %p")} '
                            f'({reservation.duration_hours} hrs)'
                        ),
                    },
                    'unit_amount': int(payment.amount * 100),  # Stripe uses cents
                },
                'quantity': 1,
            }
        ]
        
        # Add equipment rental as separate line item if applicable
        if reservation.equipment_fee and float(reservation.equipment_fee) > 0:
            rented_items = reservation.rented_equipment.select_related('equipment').all()
            for rental in rented_items:
                line_items.append({
                    'price_data': {
                        'currency': 'php',
                        'product_data': {
                            'name': f'Equipment: {rental.equipment.name}',
                        },
                        'unit_amount': int(rental.rental_fee * 100),
                    },
                    'quantity': rental.quantity,
                })
        
        # Configure payment method types
        payment_method_types = ['card']
        # Only add GCash if in production mode (requires Stripe activation)
        if not settings.DEBUG:
            payment_method_types.append('gcash')
        
        session = stripe.checkout.Session.create(
            payment_method_types=payment_method_types,
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=reservation.user.email if reservation.user.email else None,
            metadata={
                'payment_id': str(payment.id),
                'reservation_id': str(reservation.id),
                'user_id': str(reservation.user.id),
            },
            expires_at=int((timezone.now() + timedelta(hours=1)).timestamp()),
        )
        
        return session
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout session creation failed: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {e}", exc_info=True)
        return None


def create_payment_intent(payment):
    """
    Create a Stripe PaymentIntent for direct card payment on the checkout page.
    
    Returns the PaymentIntent object or None on error.
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(payment.amount * 100),  # PHP in cents
            currency='php',
            metadata={
                'payment_id': str(payment.id),
                'reservation_id': str(payment.reservation.id),
            },
            description=f'PickleSphere Reservation #{payment.reservation.id}',
        )
        return intent
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe PaymentIntent creation failed: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating PaymentIntent: {e}", exc_info=True)
        return None


def process_stripe_webhook(payload, sig_header):
    """
    Process an incoming Stripe webhook event.
    
    Returns a tuple of (event_type, event) or (None, None) on error.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event.type, event
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe webhook signature verification failed: {e}")
        return None, None
    except ValueError as e:
        logger.error(f"Invalid Stripe webhook payload: {e}")
        return None, None


@transaction.atomic
def handle_checkout_session_completed(session):
    """
    Handle a checkout.session.completed webhook event.
    Marks the payment as paid and confirms the reservation.
    Retrieves the receipt URL from the associated charge.
    """
    from .models import Payment, PaymentLog
    
    payment_id = session.get('metadata', {}).get('payment_id')
    if not payment_id:
        logger.error("Checkout session completed webhook missing payment_id in metadata")
        return False
    
    try:
        payment = Payment.objects.select_related('reservation').get(id=payment_id)
    except Payment.DoesNotExist:
        logger.error(f"Payment #{payment_id} not found for checkout session completion")
        return False
    
    # Get the PaymentIntent to access charge details (receipt_url is on the Charge, not Session)
    payment_intent_id = session.get('payment_intent')
    receipt_url = ''
    charge_id = None
    payment_method_type = 'card'
    
    if payment_intent_id:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            charge_id = intent.get('latest_charge')
            if charge_id:
                charge = stripe.Charge.retrieve(charge_id)
                receipt_url = charge.get('receipt_url', '')
            # Get the actual payment method used
            if intent.get('charges') and intent['charges']['data']:
                charge_data = intent['charges']['data'][0]
                pm_details = charge_data.get('payment_method_details', {})
                payment_method_type = pm_details.get('type', 'card')
        except stripe.error.StripeError as e:
            logger.warning(f"Could not retrieve Stripe charge details: {e}")
    
    # Update payment with Stripe details
    payment.status = 'paid'
    payment.method = 'card'
    payment.stripe_checkout_session_id = session.get('id')
    payment.stripe_payment_intent_id = payment_intent_id
    payment.transaction_id = (payment_intent_id or '')[:8].upper()
    payment.stripe_receipt_url = receipt_url
    payment.stripe_charge_id = charge_id
    payment.stripe_payment_method = payment_method_type
    
    payment.save()
    
    # Confirm the reservation
    reservation = payment.reservation
    reservation.status = 'confirmed'
    reservation.save()
    
    # Log the payment
    PaymentLog.objects.create(
        payment=payment,
        action='Stripe Payment Completed',
        details=f'Stripe Checkout Session {session.get("id")}. Payment method: {payment_method_type}',
    )
    
    # Notify the user
    from notifications.models import Notification
    Notification.objects.create(
        user=reservation.user,
        title='Payment Successful!',
        message=f'Your payment of ₱{payment.amount} for reservation #{reservation.id} has been confirmed via Stripe. Your reservation is confirmed!',
        notification_type='success',
        category='payment',
        priority='normal',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='View Reservation',
    )
    
    logger.info(f"Payment #{payment.id} completed via Stripe Checkout Session {session.get('id')}")
    return True


@transaction.atomic
def handle_payment_intent_succeeded(intent):
    """
    Handle a payment_intent.succeeded webhook event.
    """
    from .models import Payment, PaymentLog
    
    payment_id = intent.get('metadata', {}).get('payment_id')
    if not payment_id:
        logger.error("Payment intent succeeded webhook missing payment_id in metadata")
        return False
    
    try:
        payment = Payment.objects.select_related('reservation').get(id=payment_id)
    except Payment.DoesNotExist:
        logger.error(f"Payment #{payment_id} not found for payment intent succeeded")
        return False
    
    # Only process if still pending (avoid double processing)
    if payment.status != 'pending':
        logger.info(f"Payment #{payment.id} already processed (status={payment.status}), skipping")
        return True
    
    payment.status = 'paid'
    payment.method = 'card'
    payment.stripe_payment_intent_id = intent.get('id')
    payment.transaction_id = intent.get('id', '')[:8].upper()
    payment.stripe_charge_id = intent.get('latest_charge')
    
    if intent.get('charges') and intent['charges']['data']:
        charge = intent['charges']['data'][0]
        payment.stripe_receipt_url = charge.get('receipt_url', '')
        payment.stripe_payment_method = charge.get('payment_method_details', {}).get('type', 'card')
    
    payment.save()
    
    # Confirm the reservation
    reservation = payment.reservation
    reservation.status = 'confirmed'
    reservation.save()
    
    # Log
    PaymentLog.objects.create(
        payment=payment,
        action='Stripe Payment Intent Succeeded',
        details=f'Stripe PI: {intent.get("id")}. Method: {payment.stripe_payment_method or "card"}',
    )
    
    # Notify user
    from notifications.models import Notification
    Notification.objects.create(
        user=reservation.user,
        title='Payment Successful!',
        message=f'Your payment of ₱{payment.amount} for reservation #{reservation.id} has been confirmed. Your reservation is confirmed!',
        notification_type='success',
        category='payment',
        priority='normal',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='View Reservation',
    )
    
    logger.info(f"Payment #{payment.id} completed via Stripe PaymentIntent {intent.get('id')}")
    return True


@transaction.atomic
def handle_payment_intent_payment_failed(intent):
    """
    Handle a payment_intent.payment_failed webhook event.
    """
    from .models import Payment, PaymentLog
    
    payment_id = intent.get('metadata', {}).get('payment_id')
    if not payment_id:
        return False
    
    try:
        payment = Payment.objects.select_related('reservation').get(id=payment_id)
    except Payment.DoesNotExist:
        return False
    
    last_error = intent.get('last_payment_error', {})
    error_message = last_error.get('message', 'Unknown error')
    
    payment.status = 'failed'
    payment.payment_notes = f'Stripe payment failed: {error_message}'
    payment.save()
    
    PaymentLog.objects.create(
        payment=payment,
        action='Stripe Payment Failed',
        details=f'Stripe PI: {intent.get("id")}. Error: {error_message}',
    )
    
    logger.warning(f"Payment #{payment.id} failed: {error_message}")
    return True


@transaction.atomic
def process_stripe_refund(payment, amount=None):
    """
    Process a refund via Stripe.
    
    Args:
        payment: The Payment object to refund
        amount: Optional amount to refund (None = full refund)
    
    Returns:
        The Stripe Refund object or None on error
    """
    from .models import PaymentLog
    
    # Determine which Stripe identifier to use
    stripe_id = payment.stripe_payment_intent_id or payment.stripe_charge_id
    if not stripe_id:
        logger.error(f"Cannot refund payment #{payment.id}: no Stripe ID found")
        return None
    
    try:
        refund_kwargs = {
            'payment_intent': stripe_id,
            'metadata': {
                'payment_id': str(payment.id),
                'reservation_id': str(payment.reservation.id),
            },
        }
        
        if amount is not None and amount < payment.amount:
            refund_kwargs['amount'] = int(amount * 100)  # PHP in cents
        
        refund = stripe.Refund.create(**refund_kwargs)
        
        # Log the refund
        PaymentLog.objects.create(
            payment=payment,
            action='Stripe Refund Processed',
            details=f'Stripe Refund: {refund.id}. Amount: ₱{amount or payment.amount}',
        )
        
        logger.info(f"Stripe refund {refund.id} processed for payment #{payment.id}")
        return refund
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund failed for payment #{payment.id}: {e}", exc_info=True)
        PaymentLog.objects.create(
            payment=payment,
            action='Stripe Refund Failed',
            details=f'Error: {str(e)}',
        )
        return None


def get_publishable_key():
    """Get the Stripe publishable key for use in templates."""
    return getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
