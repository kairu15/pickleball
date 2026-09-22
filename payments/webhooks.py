"""
Stripe Webhook Handler for PickleSphere

Processes incoming Stripe webhook events:
- checkout.session.completed
- payment_intent.succeeded
- payment_intent.payment_failed
- charge.refunded

All webhook endpoints are CSRF-exempt and require signature verification.
"""

import json
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .stripe_integration import (
    process_stripe_webhook,
    handle_checkout_session_completed,
    handle_payment_intent_succeeded,
    handle_payment_intent_payment_failed,
)

logger = logging.getLogger(__name__)


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
    
    logger.info(f"Stripe webhook received: {event_type}")
    
    # Handle specific event types
    try:
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            success = handle_checkout_session_completed(session)
            if success:
                logger.info(f"Checkout session {session.get('id')} processed successfully")
                return HttpResponse(status=200)
            else:
                logger.error(f"Failed to process checkout session {session.get('id')}")
                return HttpResponse(status=500)
        
        elif event_type == 'payment_intent.succeeded':
            intent = event['data']['object']
            success = handle_payment_intent_succeeded(intent)
            if success:
                logger.info(f"Payment intent {intent.get('id')} processed successfully")
                return HttpResponse(status=200)
            else:
                logger.error(f"Failed to process payment intent {intent.get('id')}")
                return HttpResponse(status=500)
        
        elif event_type == 'payment_intent.payment_failed':
            intent = event['data']['object']
            handle_payment_intent_payment_failed(intent)
            return HttpResponse(status=200)  # Acknowledge even if processing fails
        
        elif event_type == 'charge.refunded':
            charge = event['data']['object']
            logger.info(f"Charge refunded: {charge.get('id')}")
            # Update local refund status if needed
            return HttpResponse(status=200)
        
        elif event_type == 'checkout.session.expired':
            session = event['data']['object']
            logger.info(f"Checkout session expired: {session.get('id')}")
            # Clean up: mark the associated payment as failed and cancel the pending reservation
            payment_id = session.get('metadata', {}).get('payment_id')
            if payment_id:
                from .models import Payment
                try:
                    payment = Payment.objects.select_related('reservation').get(id=payment_id)
                    if payment.status == 'pending':
                        payment.status = 'failed'
                        payment.payment_notes = 'Stripe checkout session expired'
                        payment.save()
                        # Cancel the pending reservation too
                        reservation = payment.reservation
                        if reservation.status == 'pending':
                            reservation.status = 'cancelled'
                            reservation.save()
                        logger.info(f"Payment #{payment.id} and reservation #{reservation.id} cancelled due to expired Stripe session")
                except Payment.DoesNotExist:
                    logger.warning(f"Payment #{payment_id} not found for expired session cleanup")
            return HttpResponse(status=200)
        
        else:
            # Unhandled event types - acknowledge receipt
            logger.debug(f"Unhandled Stripe webhook event type: {event_type}")
            return HttpResponse(status=200)
            
    except Exception as e:
        logger.error(f"Error processing Stripe webhook event {event_type}: {e}", exc_info=True)
        return HttpResponse(status=500)
