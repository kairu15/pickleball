"""
Centralized Email Service for PickleSphere.
Provides reliable email delivery with retry logic, logging, and SMTP configuration.
"""
import logging
import re
from datetime import datetime
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, BadHeaderError, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from .models import EmailLog, SmtpConfiguration

logger = logging.getLogger(__name__)

# Compiled regex for email validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class EmailValidationError(Exception):
    """Raised when email validation fails."""
    pass


class EmailSendingError(Exception):
    """Raised when email sending fails after all retries."""
    pass


def validate_email_address(email):
    """
    Validate an email address format.
    Returns True if valid, False otherwise.
    """
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def get_smtp_config():
    """
    Get the active SMTP configuration from the database.
    Falls back to Django settings if no DB config exists.
    Returns a dict of email backend settings.
    """
    try:
        smtp = SmtpConfiguration.objects.filter(is_active=True, status='enabled').first()
        if smtp:
            enc = smtp.get_encryption_settings()
            return {
                'host': smtp.smtp_host,
                'port': smtp.smtp_port,
                'username': smtp.smtp_username,
                'password': smtp.smtp_password,
                'use_tls': enc.get('use_tls', True),
                'use_ssl': enc.get('use_ssl', False),
                'sender_name': smtp.sender_name,
                'sender_email': smtp.sender_email,
            }
    except Exception as e:
        logger.warning(f"Could not load SMTP config from DB: {e}. Falling back to settings.")

    # Fallback to Django settings
    return {
        'host': settings.EMAIL_HOST,
        'port': settings.EMAIL_PORT,
        'username': settings.EMAIL_HOST_USER,
        'password': settings.EMAIL_HOST_PASSWORD,
        'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
        'use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
        'sender_name': getattr(settings, 'DEFAULT_FROM_NAME', 'PickleSphere'),
        'sender_email': settings.DEFAULT_FROM_EMAIL,
    }


def send_email(
    recipient_email,
    subject,
    html_template,
    context=None,
    recipient_name='',
    email_type='',
    from_email=None,
    reply_to=None,
    cc=None,
    bcc=None,
    attachments=None,
    related_object_id=None,
    related_object_type=None,
    sent_by_user=None,
    max_retries=3,
):
    """
    Centralized email sending function with retry logic and logging.
    
    Args:
        recipient_email (str): Recipient's email address
        subject (str): Email subject
        html_template (str): Path to HTML template (e.g., 'emails/welcome.html')
        context (dict): Template context variables
        recipient_name (str): Recipient's name for logging
        email_type (str): Type of email (e.g., 'welcome', 'password_reset')
        from_email (str): Sender email (uses config if None)
        reply_to (list): Reply-to addresses
        cc (list): CC addresses
        bcc (list): BCC addresses
        attachments (list): List of attachment tuples (filename, content, mimetype)
        related_object_id (str): ID of related object (e.g., reservation ID)
        related_object_type (str): Model name (e.g., 'Reservation')
        sent_by_user (User): User who triggered this email
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Validate email
    if not validate_email_address(recipient_email):
        logger.error(f"Invalid email address: {recipient_email}")
        return False

    if context is None:
        context = {}

    # Add common context
    context.setdefault('site_name', getattr(settings, 'SITE_NAME', 'PickleSphere'))
    context.setdefault('site_url', getattr(settings, 'SITE_URL', 'http://localhost:8000'))
    context.setdefault('current_year', timezone.now().year)

    # Create email log entry
    email_log = EmailLog.objects.create(
        recipient=recipient_email,
        recipient_name=recipient_name,
        subject=f'[{context.get("site_name")}] {subject}',
        email_type=email_type,
        status='pending',
        max_retries=max_retries,
        related_object_id=str(related_object_id) if related_object_id else None,
        related_object_type=related_object_type,
        sent_by_user=sent_by_user,
    )

    # Get SMTP config
    smtp_config = get_smtp_config()

    sender = from_email or smtp_config.get('sender_email', settings.DEFAULT_FROM_EMAIL)
    sender_name = smtp_config.get('sender_name', getattr(settings, 'DEFAULT_FROM_NAME', 'PickleSphere'))
    from_address = f'{sender_name} <{sender}>'

    # Build email content
    try:
        html_content = render_to_string(html_template, context)
        text_content = strip_tags(html_content)
    except Exception as e:
        logger.error(f"Failed to render email template '{html_template}': {e}")
        email_log.mark_failed(f'Template render error: {e}')
        return False

    # Set subject prefix
    full_subject = f'[{context.get("site_name")}] {subject}'

    # Build email message
    msg = EmailMultiAlternatives(
        subject=full_subject,
        body=text_content,
        from_email=from_address,
        to=[recipient_email],
        cc=cc or [],
        bcc=bcc or [],
        reply_to=reply_to or [sender],
    )
    msg.attach_alternative(html_content, 'text/html')

    # Attach files if any
    if attachments:
        for attachment in attachments:
            if len(attachment) == 3:
                msg.attach(*attachment)

    # Create SMTP connection from DB config if available (overrides EMAIL_BACKEND)
    connection = None
    if smtp_config.get('host') and smtp_config.get('port') and smtp_config.get('username'):
        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=smtp_config['host'],
                port=smtp_config['port'],
                username=smtp_config['username'],
                password=smtp_config['password'],
                use_tls=smtp_config.get('use_tls', True),
                use_ssl=smtp_config.get('use_ssl', False),
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(f"Failed to create SMTP connection from config: {e}. Falling back to default backend.")

    # Attempt to send with retries
    last_error = None
    actual_retries = 0
    try:
        for attempt in range(max_retries):
            try:
                if connection:
                    connection.send_messages([msg])
                else:
                    msg.send()
                email_log.mark_sent()
                logger.info(f"Email sent: {email_type} -> {recipient_email} (subject: {full_subject[:60]})")
                return True
            except Exception as e:
                last_error = e
                actual_retries = attempt + 1
                logger.warning(
                    f"Email send attempt {attempt + 1}/{max_retries} failed for "
                    f"{recipient_email}: {e}"
                )
                if connection and attempt < max_retries - 1:
                    # Reopen connection for retry in case it's in a bad state.
                    # Guard this too: a failed auth during open() must not
                    # escape as an unhandled exception (e.g. SMTPAuthenticationError).
                    try:
                        connection.close()
                    except Exception:
                        pass
                    try:
                        connection.open()
                    except Exception as open_error:
                        last_error = open_error
                        logger.warning(
                            f"Failed to reopen SMTP connection for retry "
                            f"{attempt + 2}/{max_retries}: {open_error}"
                        )
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

    # All attempts failed - pass actual retry count
    email_log.status = 'failed'
    email_log.error_message = str(last_error)[:1000]
    email_log.retry_count = actual_retries
    email_log.save(update_fields=['status', 'error_message', 'retry_count'])
    logger.error(f"Email failed: {email_type} -> {recipient_email}: Failed after {actual_retries} attempt(s): {last_error}")
    return False


def send_email_to_user(
    user,
    subject,
    html_template,
    context=None,
    email_type='',
    reply_to=None,
    cc=None,
    bcc=None,
    attachments=None,
    related_object_id=None,
    related_object_type=None,
):
    """
    Convenience function to send email to a User object.
    
    Args:
        user: User object (must have email)
        subject: Email subject
        html_template: Path to HTML template
        context: Template context
        email_type: Type identifier for logging
        reply_to, cc, bcc, attachments: As in send_email()
        related_object_id, related_object_type: For logging
    """
    if not user or not user.email:
        logger.warning(f"Cannot send email: user {user} has no email address")
        return False

    if context is None:
        context = {}

    context.setdefault('user', user)
    context.setdefault('username', user.username)
    context.setdefault('full_name', user.get_full_name() or user.username)

    return send_email(
        recipient_email=user.email,
        subject=subject,
        html_template=html_template,
        context=context,
        recipient_name=user.get_full_name() or user.username,
        email_type=email_type,
        reply_to=reply_to,
        cc=cc,
        bcc=bcc,
        attachments=attachments,
        related_object_id=related_object_id,
        related_object_type=related_object_type,
        sent_by_user=user,
    )
