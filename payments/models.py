from django.db import models
from reservations.models import Reservation

from utils.validators import IMAGE_UPLOAD_VALIDATORS


class PaymentSettings(models.Model):
    """
    Global, system-wide payment information shown to users on the checkout page.
    Managed exclusively by the Super Admin.
    """

    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
        ('maya', 'Maya'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
    ]

    # GCash
    gcash_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='GCash mobile number shown to users when paying'
    )
    gcash_account_name = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Name registered on the GCash account'
    )

    # Maya
    maya_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Maya mobile number shown to users when paying'
    )
    maya_account_name = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Name registered on the Maya account'
    )

    # Bank Transfer
    bank_name = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='e.g. BDO, BPI, UnionBank'
    )
    bank_account_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)

    # QR Code
    qr_code = models.ImageField(
        upload_to='payments/qr/', blank=True, null=True,
        validators=IMAGE_UPLOAD_VALIDATORS,
        help_text='QR code image for payments (shown on the checkout page)'
    )

    # Instructions & Accepted Methods
    payment_instructions = models.TextField(
        blank=True, null=True,
        help_text='Step-by-step instructions shown to users when paying'
    )
    accepted_payment_methods = models.JSONField(
        default=list, blank=True,
        help_text='Payment methods accepted by the system'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Enable online payment submissions'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_settings'
        verbose_name = 'Payment Settings'
        verbose_name_plural = 'Payment Settings'

    def __str__(self):
        return 'System Payment Settings'

    @property
    def has_gcash(self):
        return bool(self.gcash_number and self.gcash_account_name)

    @property
    def has_maya(self):
        return bool(self.maya_number and self.maya_account_name)

    @property
    def has_bank(self):
        return bool(self.bank_name and self.bank_account_name and self.bank_account_number)

    @property
    def is_configured(self):
        """True when at least one complete payment account has been configured."""
        return any([self.has_gcash, self.has_maya, self.has_bank])

    def accepts(self, method):
        return method in (self.accepted_payment_methods or [])

    @property
    def enabled_methods(self):
        """Accepted methods that are fully configured and can be offered at checkout.
        Returns an empty list when online payments are disabled."""
        if not self.is_active:
            return []
        methods = self.accepted_payment_methods or []
        result = []
        if 'gcash' in methods and self.has_gcash:
            result.append('gcash')
        if 'maya' in methods and self.has_maya:
            result.append('maya')
        if 'bank_transfer' in methods and self.has_bank:
            result.append('bank_transfer')
        return result


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )
    
    METHOD_CHOICES = (
        ('gcash', 'GCash'),
        ('maya', 'Maya'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
    )
    
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True, null=True)
    
    # For GCash payments (also used as generic proof of payment for any method)
    gcash_reference = models.CharField(max_length=100, blank=True, null=True)
    gcash_proof_image = models.ImageField(
        upload_to='payments/gcash/', blank=True, null=True,
        validators=IMAGE_UPLOAD_VALIDATORS,
    )

    # For cash payments
    cash_received_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_payments_received')
    cash_received_at = models.DateTimeField(null=True, blank=True)
    
    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    payment_notes = models.TextField(blank=True, null=True)

    # Stripe integration fields
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text='Stripe PaymentIntent ID (pi_xxx)')
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text='Stripe Checkout Session ID (cs_xxx)')
    stripe_payment_method = models.CharField(max_length=50, blank=True, null=True, help_text='Stripe payment method type (card, gcash, grabpay, etc.)')
    stripe_receipt_url = models.URLField(max_length=500, blank=True, null=True, help_text='URL to the Stripe-hosted receipt')
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True, help_text='Stripe Charge ID (ch_xxx)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reservation', 'status']),
            models.Index(fields=['method', 'status']),
        ]
    
    def __str__(self):
        return f"Payment #{self.id} - {self.reservation.user.username} - ₱{self.amount}"


class Refund(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    )
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Stripe refund ID (re_xxx) when the refund originated from Stripe. Unique so
    # webhook deliveries for the same refund are idempotent.
    stripe_refund_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True,
        help_text='Stripe Refund ID (re_xxx) for refunds mirrored from Stripe',
    )
    
    requested_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='refund_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_refunds')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'refunds'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['status', '-requested_at']),
        ]
    
    def __str__(self):
        return f"Refund #{self.id} - Payment #{self.payment.id} - ₱{self.amount}"


class StripeWebhookEvent(models.Model):
    """One row per processed Stripe webhook event (event.id, e.g. evt_xxx).

    Stripe delivers webhooks at least once and retries on failure, so handlers
    must be idempotent. A row is written before a handler runs and deleted again
    if the handler fails, so a failed event can still be retried while a
    successful one is never processed twice.
    """

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stripe_webhook_events'
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['event_type', '-processed_at']),
        ]

    def __str__(self):
        return f'{self.event_type} ({self.event_id})'


class PaymentLog(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.payment.id} - {self.action}"
