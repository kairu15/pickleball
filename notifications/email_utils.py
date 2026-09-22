"""
Email utility module for PickleSphere transactional emails.
Uses the centralized email_service for reliable delivery with retry logic and logging.
"""
from django.conf import settings
from .email_service import send_email_to_user, send_email, validate_email_address


# ==================== AUTHENTICATION EMAILS


# ==================== AUTHENTICATION EMAILS ====================

def send_welcome_email(user):
    """Send welcome email to new users after successful registration."""
    return send_email_to_user(
        user=user,
        subject='Welcome to PickleSphere!',
        html_template='emails/welcome.html',
        context={
            'title': 'Welcome to PickleSphere!',
            'username': user.username,
            'action_url': f'{settings.SITE_URL}/',
            'action_text': 'Get Started',
        },
        email_type='welcome',
    )


def send_email_verification_email(user, verification_url):
    """Send email verification link to user."""
    return send_email_to_user(
        user=user,
        subject='Verify Your Email Address',
        html_template='emails/email_verification.html',
        context={
            'title': 'Verify Your Email',
            'verification_url': verification_url,
            'action_url': verification_url,
            'action_text': 'Verify Email',
            'expires_in': '24 hours',
        },
        email_type='email_verification',
    )


def send_password_reset_email(user, reset_url):
    """Send password reset email with reset link."""
    return send_email_to_user(
        user=user,
        subject='Password Reset Request',
        html_template='emails/password_reset.html',
        context={
            'title': 'Password Reset',
            'reset_url': reset_url,
            'action_url': reset_url,
            'action_text': 'Reset Password',
            'expires_in': '1 hour',
        },
        email_type='password_reset',
    )


def send_password_changed_email(user):
    """Send notification that password was changed successfully."""
    return send_email_to_user(
        user=user,
        subject='Password Changed Successfully',
        html_template='emails/password_changed.html',
        context={
            'title': 'Password Changed',
            'message': 'Your password has been changed successfully. If you did not make this change, please contact support immediately.',
            'action_url': f'{settings.SITE_URL}/accounts/login/',
            'action_text': 'Sign In',
        },
        email_type='password_changed',
    )


def send_login_security_alert_email(user, ip_address, user_agent=''):
    """Send security alert for suspicious login activity."""
    return send_email_to_user(
        user=user,
        subject='New Sign-In to Your Account',
        html_template='emails/security_alert.html',
        context={
            'title': 'New Sign-In Alert',
            'alert_type': 'login',
            'message': f'We noticed a new sign-in to your PickleSphere account.',
            'ip_address': ip_address,
            'user_agent': user_agent,
            'action_url': f'{settings.SITE_URL}/accounts/profile/',
            'action_text': 'Review Account',
        },
        email_type='security_alert',
    )


# ==================== USER ACCOUNT EMAILS ====================

def send_account_update_email(user, message_text):
    """Send account update notification."""
    return send_email_to_user(
        user=user,
        subject='Account Updated',
        html_template='emails/account_update.html',
        context={
            'title': 'Account Updated',
            'message_text': message_text,
            'action_url': f'{settings.SITE_URL}/accounts/profile/',
            'action_text': 'View Profile',
        },
        email_type='account_update',
    )


def send_account_suspension_email(user, reason=''):
    """Send notification that account has been suspended."""
    return send_email_to_user(
        user=user,
        subject='Account Suspended',
        html_template='emails/account_suspension.html',
        context={
            'title': 'Account Suspended',
            'reason': reason,
            'message': 'Your PickleSphere account has been suspended.' + (f' Reason: {reason}' if reason else ''),
            'action_url': f'{settings.SITE_URL}/contact/',
            'action_text': 'Contact Support',
        },
        email_type='account_suspension',
    )


def send_account_reactivation_email(user):
    """Send notification that account has been reactivated."""
    return send_email_to_user(
        user=user,
        subject='Account Reactivated',
        html_template='emails/account_reactivation.html',
        context={
            'title': 'Account Reactivated',
            'message': 'Your PickleSphere account has been reactivated. You can now sign in and use all features.',
            'action_url': f'{settings.SITE_URL}/accounts/login/',
            'action_text': 'Sign In',
        },
        email_type='account_reactivation',
    )


def send_account_deletion_email(user):
    """Send confirmation that account has been deleted."""
    return send_email_to_user(
        user=user,
        subject='Account Deletion Confirmation',
        html_template='emails/account_deletion.html',
        context={
            'title': 'Account Deleted',
            'message': 'Your PickleSphere account has been permanently deleted. We\'re sorry to see you go.',
            'action_url': f'{settings.SITE_URL}/',
            'action_text': 'Visit PickleSphere',
        },
        email_type='account_deletion',
    )


# ==================== RESERVATION EMAILS ====================

def send_reservation_reminder_email(user, reservation):
    """
    Send a reminder email 24 hours before a confirmed reservation.
    """
    return send_email_to_user(
        user=user,
        subject=f'Reminder: Your Court Reservation Tomorrow!',
        html_template='emails/reservation_reminder.html',
        context={
            'title': 'Reservation Reminder',
            'reservation': reservation,
            'court_name': reservation.court.name,
            'court_location': getattr(reservation.court, 'location', ''),
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'start_time': reservation.start_time.strftime('%I:%M %p'),
            'end_time': reservation.end_time.strftime('%I:%M %p'),
            'duration_hours': float(reservation.duration_hours),
            'reservation_id': reservation.id,
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'View Reservation',
            'cancel_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/cancel/',
        },
        email_type='reservation_reminder',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


def send_reservation_submitted_email(user, reservation):
    """Send email when reservation is submitted (pending)."""
    return send_email_to_user(
        user=user,
        subject='Reservation Submitted',
        html_template='emails/reservation_submitted.html',
        context={
            'title': 'Reservation Submitted',
            'reservation': reservation,
            'court_name': reservation.court.name,
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'start_time': reservation.start_time.strftime('%I:%M %p'),
            'end_time': reservation.end_time.strftime('%I:%M %p'),
            'reservation_id': reservation.id,
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'View Reservation',
        },
        email_type='reservation_submitted',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


def send_reservation_confirmed_email(user, reservation):
    """Send reservation confirmation email."""
    # Link to the in-app directions page when the court site has coordinates set
    court = reservation.court
    site = getattr(court, 'site', None)
    has_coordinates = bool(site and site.latitude and site.longitude)
    directions_url = f'{settings.SITE_URL}/courts/{court.id}/directions/' if has_coordinates else ''
    return send_email_to_user(
        user=user,
        subject='Reservation Confirmed!',
        html_template='emails/reservation_confirmed.html',
        context={
            'title': 'Reservation Confirmed!',
            'reservation': reservation,
            'court_name': court.name,
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'start_time': reservation.start_time.strftime('%I:%M %p'),
            'end_time': reservation.end_time.strftime('%I:%M %p'),
            'reservation_id': reservation.id,
            'amount': getattr(reservation, 'total_amount', 'N/A'),
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'View Reservation',
            'directions_url': directions_url,
        },
        email_type='reservation_confirmed',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


def send_reservation_rejected_email(user, reservation, reason=''):
    """Send reservation rejection email."""
    return send_email_to_user(
        user=user,
        subject='Reservation Not Approved',
        html_template='emails/reservation_rejected.html',
        context={
            'title': 'Reservation Not Approved',
            'reservation': reservation,
            'court_name': reservation.court.name,
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'reservation_id': reservation.id,
            'reason': reason,
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'View Details',
        },
        email_type='reservation_rejected',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


def send_reservation_cancelled_email(user, reservation):
    """Send reservation cancellation email."""
    return send_email_to_user(
        user=user,
        subject='Reservation Cancelled',
        html_template='emails/reservation_cancelled.html',
        context={
            'title': 'Reservation Cancelled',
            'reservation': reservation,
            'court_name': reservation.court.name,
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'reservation_id': reservation.id,
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'View Details',
        },
        email_type='reservation_cancelled',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


def send_reservation_completed_email(user, reservation):
    """Send reservation completion email."""
    return send_email_to_user(
        user=user,
        subject='Reservation Complete',
        html_template='emails/reservation_completed.html',
        context={
            'title': 'Reservation Complete',
            'reservation': reservation,
            'court_name': reservation.court.name,
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'reservation_id': reservation.id,
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'Leave a Rating',
        },
        email_type='reservation_completed',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


def send_reservation_modification_email(user, reservation, changes_desc=''):
    """Send reservation modification notification."""
    return send_email_to_user(
        user=user,
        subject='Reservation Modified',
        html_template='emails/reservation_modified.html',
        context={
            'title': 'Reservation Modified',
            'reservation': reservation,
            'court_name': reservation.court.name,
            'date': reservation.date.strftime('%A, %B %d, %Y'),
            'start_time': reservation.start_time.strftime('%I:%M %p'),
            'end_time': reservation.end_time.strftime('%I:%M %p'),
            'reservation_id': reservation.id,
            'changes': changes_desc,
            'action_url': f'{settings.SITE_URL}/user/reservations/{reservation.id}/',
            'action_text': 'View Updated Reservation',
        },
        email_type='reservation_modified',
        related_object_id=str(reservation.id),
        related_object_type='Reservation',
    )


# ==================== PAYMENT EMAILS ====================

def send_payment_confirmed_email(user, payment):
    """Send payment confirmation email."""
    return send_email_to_user(
        user=user,
        subject='Payment Confirmed!',
        html_template='emails/payment_confirmed.html',
        context={
            'title': 'Payment Confirmed!',
            'payment': payment,
            'amount': payment.amount,
            'method': payment.get_method_display() if hasattr(payment, 'get_method_display') else payment.method,
            'reference': payment.transaction_id or f'#{payment.id}',
            'payment_id': payment.id,
            'reservation': payment.reservation,
            'action_url': f'{settings.SITE_URL}/user/payments/',
            'action_text': 'View Payments',
        },
        email_type='payment_confirmed',
        related_object_id=str(payment.id),
        related_object_type='Payment',
    )


def send_payment_receipt_email(user, payment):
    """Send payment receipt with full details."""
    return send_email_to_user(
        user=user,
        subject=f'Payment Receipt - #{payment.id}',
        html_template='emails/payment_receipt.html',
        context={
            'title': 'Payment Receipt',
            'payment': payment,
            'amount': payment.amount,
            'method': payment.get_method_display() if hasattr(payment, 'get_method_display') else payment.method,
            'reference': payment.transaction_id or f'#{payment.id}',
            'payment_id': payment.id,
            'reservation': payment.reservation,
            'action_url': f'{settings.SITE_URL}/user/payments/{payment.id}/receipt/',
            'action_text': 'View Receipt',
        },
        email_type='payment_receipt',
        related_object_id=str(payment.id),
        related_object_type='Payment',
    )


def send_payment_verification_email(user, payment):
    """Send notification that payment is pending verification."""
    return send_email_to_user(
        user=user,
        subject='Payment Pending Verification',
        html_template='emails/payment_verification.html',
        context={
            'title': 'Payment Pending Verification',
            'payment': payment,
            'amount': payment.amount,
            'method': payment.get_method_display() if hasattr(payment, 'get_method_display') else payment.method,
            'payment_id': payment.id,
            'reservation': payment.reservation,
            'action_url': f'{settings.SITE_URL}/user/payments/',
            'action_text': 'View Payments',
        },
        email_type='payment_verification',
        related_object_id=str(payment.id),
        related_object_type='Payment',
    )


def send_payment_failed_email(user, payment, reason=''):
    """Send payment failure notification."""
    return send_email_to_user(
        user=user,
        subject='Payment Failed',
        html_template='emails/payment_failed.html',
        context={
            'title': 'Payment Failed',
            'payment': payment,
            'amount': payment.amount,
            'reason': reason,
            'reservation': payment.reservation,
            'action_url': f'{settings.SITE_URL}/user/payments/',
            'action_text': 'Try Again',
        },
        email_type='payment_failed',
        related_object_id=str(payment.id),
        related_object_type='Payment',
    )


def send_refund_confirmed_email(user, cancellation):
    """Send refund confirmation email."""
    res = cancellation.reservation
    refund_amount = float(res.total_amount) - float(cancellation.deduction_amount)
    return send_email_to_user(
        user=user,
        subject='Refund Processed',
        html_template='emails/refund_processed.html',
        context={
            'title': 'Refund Processed',
            'cancellation': cancellation,
            'reservation': res,
            'refund_amount': refund_amount,
            'court_name': res.court.name,
            'date': res.date.strftime('%A, %B %d, %Y'),
            'reservation_id': res.id,
            'action_url': f'{settings.SITE_URL}/user/payments/',
            'action_text': 'View Payments',
        },
        email_type='refund_confirmed',
        related_object_id=str(cancellation.id),
        related_object_type='CancellationRequest',
    )


# ==================== EQUIPMENT EMAILS ====================

def send_equipment_rental_email(user, equipment, status):
    """Send equipment rental status email."""
    status_labels = {
        'reserved': 'Equipment Reserved',
        'rented': 'Equipment Ready for Pickup',
        'returned': 'Equipment Returned',
        'cancelled': 'Equipment Rental Cancelled',
        'overdue': 'Equipment Overdue!',
    }
    return send_email_to_user(
        user=user,
        subject=status_labels.get(status, 'Equipment Update'),
        html_template='emails/equipment_rental.html',
        context={
            'title': status_labels.get(status, 'Equipment Update'),
            'equipment': equipment,
            'equipment_name': equipment.name,
            'status': status,
            'action_url': f'{settings.SITE_URL}/equipment/{equipment.id}/',
            'action_text': 'View Equipment',
        },
        email_type=f'equipment_{status}',
        related_object_id=str(equipment.id),
        related_object_type='Equipment',
    )


def send_equipment_return_reminder_email(user, equipment, rental):
    """Send reminder to return equipment."""
    return send_email_to_user(
        user=user,
        subject=f'Reminder: Return {equipment.name}',
        html_template='emails/equipment_rental.html',
        context={
            'title': 'Equipment Return Reminder',
            'equipment': equipment,
            'equipment_name': equipment.name,
            'status': 'rented',
            'due_date': rental.expected_return_date.strftime('%A, %B %d, %Y') if hasattr(rental, 'expected_return_date') and rental.expected_return_date else '',
            'action_url': f'{settings.SITE_URL}/equipment/{equipment.id}/',
            'action_text': 'View Details',
        },
        email_type='equipment_return_reminder',
        related_object_id=str(equipment.id),
        related_object_type='Equipment',
    )


def send_equipment_maintenance_email(admin_user, equipment, maintenance_type='scheduled'):
    """Send notification to admin about equipment maintenance."""
    return send_email_to_user(
        user=admin_user,
        subject=f'Equipment Maintenance: {equipment.name}',
        html_template='emails/equipment_maintenance.html',
        context={
            'title': 'Equipment Maintenance',
            'equipment': equipment,
            'equipment_name': equipment.name,
            'maintenance_type': maintenance_type,
            'type_label': 'Scheduled Maintenance' if maintenance_type == 'scheduled' else 'Maintenance Needed',
            'action_url': f'{settings.SITE_URL}/staff/equipment/',
            'action_text': 'Manage Equipment',
        },
        email_type=f'equipment_maintenance_{maintenance_type}',
        related_object_id=str(equipment.id),
        related_object_type='Equipment',
    )


# ==================== TOURNAMENT EMAILS ====================

def send_tournament_registration_email(user, tournament, status='pending'):
    """Send tournament registration status email."""
    subject_map = {
        'pending': 'Tournament Registration Submitted',
        'approved': 'Tournament Registration Approved!',
        'rejected': 'Tournament Registration Update',
    }
    return send_email_to_user(
        user=user,
        subject=subject_map.get(status, 'Tournament Registration Update'),
        html_template='emails/tournament_registration.html',
        context={
            'title': subject_map.get(status, 'Tournament Registration Update'),
            'tournament': tournament,
            'tournament_name': tournament.name,
            'status': status,
            'action_url': f'{settings.SITE_URL}/user/tournaments/',
            'action_text': 'View Tournaments',
        },
        email_type=f'tournament_registration_{status}',
        related_object_id=str(tournament.id),
        related_object_type='Tournament',
    )


def send_tournament_schedule_update_email(user, tournament, update_info=''):
    """Send tournament schedule update notification."""
    return send_email_to_user(
        user=user,
        subject=f'Schedule Updated: {tournament.name}',
        html_template='emails/tournament_schedule_update.html',
        context={
            'title': 'Tournament Schedule Updated',
            'tournament': tournament,
            'tournament_name': tournament.name,
            'update_info': update_info,
            'action_url': f'{settings.SITE_URL}/tournaments/{tournament.id}/',
            'action_text': 'View Schedule',
        },
        email_type='tournament_schedule_update',
        related_object_id=str(tournament.id),
        related_object_type='Tournament',
    )


def send_tournament_match_reminder_email(user, match):
    """Send match reminder email."""
    tournament = match.tournament
    return send_email_to_user(
        user=user,
        subject=f'Match Reminder: {tournament.name}',
        html_template='emails/match_reminder.html',
        context={
            'title': 'Match Reminder',
            'tournament': tournament,
            'tournament_name': tournament.name,
            'match': match,
            'court_name': match.court.name if match.court else 'TBD',
            'scheduled_date': match.scheduled_date.strftime('%A, %B %d, %Y') if match.scheduled_date else 'TBD',
            'scheduled_time': match.scheduled_time.strftime('%I:%M %p') if match.scheduled_time else 'TBD',
            'action_url': f'{settings.SITE_URL}/tournaments/{tournament.id}/matches/{match.id}/',
            'action_text': 'View Match',
        },
        email_type='match_reminder',
        related_object_id=str(match.id),
        related_object_type='Match',
    )


def send_tournament_cancellation_email(user, tournament):
    """Send tournament cancellation notification."""
    return send_email_to_user(
        user=user,
        subject=f'Tournament Cancelled: {tournament.name}',
        html_template='emails/tournament_cancellation.html',
        context={
            'title': 'Tournament Cancelled',
            'tournament': tournament,
            'tournament_name': tournament.name,
            'action_url': f'{settings.SITE_URL}/tournaments/',
            'action_text': 'View Tournaments',
        },
        email_type='tournament_cancelled',
        related_object_id=str(tournament.id),
        related_object_type='Tournament',
    )


def send_tournament_results_email(user, tournament, placement=''):
    """Send tournament results announcement."""
    return send_email_to_user(
        user=user,
        subject=f'Tournament Results: {tournament.name}',
        html_template='emails/tournament_results.html',
        context={
            'title': 'Tournament Results',
            'tournament': tournament,
            'tournament_name': tournament.name,
            'placement': placement,
            'action_url': f'{settings.SITE_URL}/tournaments/{tournament.id}/leaderboard/',
            'action_text': 'View Leaderboard',
        },
        email_type='tournament_results',
        related_object_id=str(tournament.id),
        related_object_type='Tournament',
    )


# ==================== CONTACT FORM EMAILS ====================

def send_contact_form_email(contact_data):
    """
    Send contact form submission to the site admin and
    send an acknowledgment to the user.
    
    Args:
        contact_data: dict with keys: name, email, subject, message
    """
    admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@picklesphere.com')
    site_name = getattr(settings, 'SITE_NAME', 'PickleSphere')
    
    # Send to admin
    send_email(
        recipient_email=admin_email,
        subject=f'Contact Form: {contact_data.get("subject", "New Message")}',
        html_template='emails/contact_form_admin.html',
        context={
            'title': 'New Contact Form Submission',
            'name': contact_data.get('name', ''),
            'email': contact_data.get('email', ''),
            'subject_line': contact_data.get('subject', ''),
            'message': contact_data.get('message', ''),
        },
        email_type='contact_form_admin',
    )
    
    # Send acknowledgment to the submitter
    if validate_email_address(contact_data.get('email', '')):
        send_email(
            recipient_email=contact_data['email'],
            subject='We Received Your Message',
            html_template='emails/contact_form_acknowledgment.html',
            context={
                'title': 'Message Received',
                'name': contact_data.get('name', ''),
                'message_preview': contact_data.get('message', '')[:200],
                'site_name': site_name,
            },
            email_type='contact_form_acknowledgment',
        )


# ==================== NOTIFICATION EMAIL ====================

def send_notification_email(user, notification_obj=None, **context_overrides):
    """Send an email notification based on a Notification object or explicit context."""
    title = context_overrides.get('title', '')
    message = context_overrides.get('message', '')
    category = context_overrides.get('category', 'system')
    
    if notification_obj:
        title = title or notification_obj.title
        message = message or notification_obj.message
        category = category or notification_obj.category

    context = {
        'title': title,
        'message': message,
        'category': category,
        'notification_type': context_overrides.get('notification_type', 'info'),
        'action_url': context_overrides.get('action_url', ''),
        'action_text': context_overrides.get('action_text', 'View Details'),
        **context_overrides,
    }
    
    return send_email_to_user(
        user=user,
        subject=title or 'PickleSphere Notification',
        html_template='emails/notification.html',
        context=context,
        email_type=f'notification_{category}',
    )


# ==================== STAFF EMAILS ====================

def send_staff_welcome_email(user, temp_password=''):
    """Send welcome email to newly created staff member."""
    return send_email_to_user(
        user=user,
        subject='Welcome to PickleSphere Staff!',
        html_template='emails/welcome.html',
        context={
            'title': 'Welcome to PickleSphere!',
            'username': user.username,
            'temp_password': temp_password,
            'has_temp_password': bool(temp_password),
            'action_url': f'{settings.SITE_URL}/accounts/login/',
            'action_text': 'Sign In',
        },
        email_type='staff_welcome',
    )


# ==================== TEST EMAIL ====================

def send_test_email(user):
    """Send a test email to verify configuration."""
    return send_email_to_user(
        user=user,
        subject='Test Email from PickleSphere',
        html_template='emails/test_email.html',
        context={
            'title': 'Test Email',
            'message': 'If you received this email, your email configuration is working correctly!',
        },
        email_type='test',
    )
