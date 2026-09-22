"""
OTP (One-Time Password) utility module for email verification.
Used for registration verification and password reset flows.
"""
import hashlib
import random
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from notifications.models import EmailOTP
from notifications.email_service import send_email

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
# Rate limiting: max resend attempts per IP in the time window
OTP_RESEND_MAX_PER_IP = 5
OTP_RESEND_WINDOW_MINUTES = 15


def generate_otp_code():
    """Generate a secure 6-digit numeric OTP code."""
    return str(random.randint(100000, 999999))


def hash_otp(otp_code):
    """Hash an OTP code using SHA-256 for secure storage."""
    return hashlib.sha256(otp_code.encode()).hexdigest()


@transaction.atomic
def create_and_send_otp(email, purpose, user=None, ip_address=None, request=None):
    """
    Generate an OTP, save it to the database, and send it via email.
    
    Args:
        email: The recipient email address
        purpose: 'registration' or 'password_reset'
        user: Optional User object (may be None during registration)
        ip_address: Optional IP address for audit logging
        request: Optional request object to build URLs
        
    Returns:
        tuple: (success: bool, otp_obj: EmailOTP or None, error: str or None)
    """
    # Invalidate any previous unused OTPs for this email/purpose
    EmailOTP.objects.filter(
        email__iexact=email,
        purpose=purpose,
        is_used=False,
        expires_at__gt=timezone.now()
    ).update(is_used=True, used_at=timezone.now())
    
    # Generate OTP
    otp_code = generate_otp_code()
    otp_hash = hash_otp(otp_code)
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Save to database
    otp_obj = EmailOTP.objects.create(
        user=user,
        email=email.lower(),
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=expires_at,
        max_attempts=OTP_MAX_ATTEMPTS,
        ip_address=ip_address,
    )
    
    # Prepare email context
    site_name = getattr(settings, 'SITE_NAME', 'PickleSphere')
    greeting = f"Hi {user.first_name}!" if user and user.first_name else "Hello!"
    
    if purpose == 'registration':
        title = 'Verify Your Email Address'
        subject = f'[{site_name}] Verify your email address'
    else:
        title = 'Password Reset Code'
        subject = f'[{site_name}] Your password reset code'
    
    # Send OTP via email
    success = send_email(
        recipient_email=email,
        subject=subject,
        html_template='emails/otp_email.html',
        context={
            'title': title,
            'greeting': greeting,
            'otp_code': list(otp_code),  # Pass as list for individual digit display
            'otp': otp_code,
            'expiry_minutes': OTP_EXPIRY_MINUTES,
            'site_name': site_name,
        },
        email_type=f'otp_{purpose}',
        related_object_id=str(otp_obj.id),
        related_object_type='EmailOTP',
    )
    
    if success:
        logger.info(f"OTP sent to {email} for {purpose} (OTP ID: {otp_obj.id})")
        return True, otp_obj, None
    else:
        logger.error(f"Failed to send OTP to {email} for {purpose}")
        return False, otp_obj, "Failed to send OTP email. Please try again."


def verify_otp_code(email, otp_code, purpose):
    """
    Verify an OTP code for the given email and purpose.
    
    Args:
        email: The email address
        otp_code: The 6-digit OTP code entered by the user
        purpose: 'registration' or 'password_reset'
        
    Returns:
        tuple: (success: bool, otp_obj: EmailOTP or None, error: str or None)
    """
    if not otp_code or len(otp_code) != OTP_LENGTH or not otp_code.isdigit():
        return False, None, "Invalid OTP format. Please enter a 6-digit code."
    
    # Find the latest valid OTP for this email/purpose
    otp_obj = EmailOTP.objects.filter(
        email__iexact=email,
        purpose=purpose,
        is_used=False,
        expires_at__gt=timezone.now(),
        attempts__lt=OTP_MAX_ATTEMPTS,
    ).order_by('-created_at').first()
    
    if not otp_obj:
        # Check if there's an expired one
        expired_otp = EmailOTP.objects.filter(
            email__iexact=email,
            purpose=purpose,
            is_used=False,
        ).order_by('-created_at').first()
        
        if expired_otp:
            if expired_otp.is_expired:
                return False, None, "OTP has expired. Please request a new one."
            if expired_otp.attempts >= expired_otp.max_attempts:
                return False, None, "Too many failed attempts. Please request a new OTP."
        
        return False, None, "No valid OTP found. Please request a new one."
    
    # Verify the OTP
    hashed_input = hash_otp(otp_code)
    
    otp_obj.attempts += 1
    
    if hashed_input == otp_obj.otp_hash:
        otp_obj.is_used = True
        otp_obj.used_at = timezone.now()
        otp_obj.save(update_fields=['is_used', 'used_at', 'attempts'])
        logger.info(f"OTP verified for {email} ({purpose})")
        return True, otp_obj, None
    else:
        otp_obj.save(update_fields=['attempts'])
        remaining = otp_obj.max_attempts - otp_obj.attempts
        if remaining <= 0:
            return False, None, "Too many failed attempts. Please request a new OTP."
        return False, None, f"Incorrect OTP. {remaining} attempt(s) remaining."


def cleanup_expired_otps():
    """
    Clean up expired OTP records from the database.
    Should be called periodically (e.g., via cron or management command).
    """
    expired = EmailOTP.objects.filter(expires_at__lt=timezone.now(), is_used=False)
    count = expired.count()
    if count:
        expired.delete()
        logger.info(f"Cleaned up {count} expired OTP records")
    return count
