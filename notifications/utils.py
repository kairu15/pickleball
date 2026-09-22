from django.utils import timezone
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationPreference
from .email_utils import send_notification_email


def _get_notification_url_name(request, base_name):
    """Returns role-appropriate URL name for notification routes."""
    user = request.user
    if user.is_super_admin():
        return f'super_admin_{base_name}'
    elif user.is_staff_member():
        return f'staff_{base_name}'
    return base_name


def create_notification(
    user,
    title='',
    message='',
    notification_type='info',
    category='system',
    priority='normal',
    action_url='',
    action_text='View Details',
    related_reservation=None,
    related_payment=None,
    related_match=None,
    related_tournament=None,
    related_equipment=None,
    check_preferences=True,
    dedup_window_minutes=5,
):
    """Centralized notification creation with preference checking and deduplication."""
    if check_preferences:
        prefs = NotificationPreference.objects.filter(user=user).first()
        if prefs and not prefs.is_category_enabled(category):
            return None

    if dedup_window_minutes > 0 and title:
        since = timezone.now() - timezone.timedelta(minutes=dedup_window_minutes)
        duplicate = Notification.objects.filter(
            user=user,
            title=title,
            category=category,
            created_at__gte=since
        ).first()
        if duplicate:
            return duplicate

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        category=category,
        priority=priority,
        action_url=action_url,
        action_text=action_text,
        related_reservation=related_reservation,
        related_payment=related_payment,
        related_match=related_match,
        related_tournament=related_tournament,
        related_equipment=related_equipment,
    )

    # Send email notification if user has email notifications enabled
    try:
        send_notification_email(
            user=user,
            notification_obj=notification,
            action_url=action_url,
            action_text=action_text,
        )
    except Exception:
        pass

    # Push real-time notification via WebSocket
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {
                    'type': 'send_notification',
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message[:200],
                    'notification_type': notification.notification_type,
                    'category': notification.category,
                    'priority': notification.priority,
                    'action_url': notification.action_url,
                    'action_text': notification.action_text,
                    'created_at': notification.created_at.isoformat() if notification.created_at else '',
                    'unread_count': Notification.objects.filter(user=user, is_read=False, is_deleted=False).count(),
                }
            )
    except Exception:
        pass

    return notification


def broadcast_to_users(users, title, message, notification_type='info', category='system', priority='normal', action_url=''):
    """Send the same notification to multiple users efficiently."""
    notifications = []
    for user in users:
        n = create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            priority=priority,
            action_url=action_url,
        )
        if n:
            notifications.append(n)
    return notifications


# ==================== USER NOTIFICATIONS ====================

def notify_user_reservation_submitted(user, reservation):
    return create_notification(
        user=user,
        title='Reservation Submitted',
        message=f'Your reservation for {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} ({reservation.start_time.strftime("%I:%M %p")} - {reservation.end_time.strftime("%I:%M %p")}) has been submitted and is pending confirmation.',
        notification_type='info',
        category='reservation',
        priority='normal',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='View Reservation',
        related_reservation=reservation,
    )

def notify_user_reservation_confirmed(user, reservation):
    return create_notification(
        user=user,
        title='Reservation Confirmed',
        message=f'Your reservation for {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} is confirmed! See you on the court.',
        notification_type='success',
        category='reservation',
        priority='normal',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='View Reservation',
        related_reservation=reservation,
    )

def notify_user_reservation_rejected(user, reservation, reason=''):
    msg = f'Your reservation for {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} has been rejected.'
    if reason:
        msg += f' Reason: {reason}'
    return create_notification(
        user=user,
        title='Reservation Rejected',
        message=msg,
        notification_type='error',
        category='cancellation',
        priority='high',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='View Details',
        related_reservation=reservation,
    )

def notify_user_reservation_cancelled(user, reservation):
    return create_notification(
        user=user,
        title='Reservation Cancelled',
        message=f'Your reservation for {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} has been cancelled.',
        notification_type='warning',
        category='cancellation',
        priority='normal',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='View Details',
        related_reservation=reservation,
    )

def notify_user_reservation_completed(user, reservation):
    return create_notification(
        user=user,
        title='Reservation Completed',
        message=f'Your reservation at {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} is complete. We hope you had a great game!',
        notification_type='success',
        category='reservation',
        priority='low',
        action_url=f'/user/reservations/{reservation.id}/',
        action_text='Leave a Rating',
        related_reservation=reservation,
    )

def notify_user_payment_confirmed(user, payment):
    return create_notification(
        user=user,
        title='Payment Confirmed',
        message=f'Your payment of ₱{payment.amount} for reservation has been confirmed. Reference: #{payment.id}',
        notification_type='success',
        category='payment',
        priority='normal',
        action_url=f'/user/payments/',
        action_text='View Payments',
        related_payment=payment,
    )

def notify_user_refund_processed(user, cancellation):
    res = cancellation.reservation
    return create_notification(
        user=user,
        title='Refund Processed',
        message=f'Your refund for reservation #{res.id} at {res.court.name} has been processed.',
        notification_type='success',
        category='refund',
        priority='normal',
        action_url=f'/user/payments/',
        action_text='View Payments',
        related_reservation=res,
    )

def notify_user_tournament_registration(user, tournament, status='pending'):
    if status == 'pending':
        title = 'Tournament Registration Submitted'
        msg = f'Your registration for {tournament.name} has been submitted and is pending approval.'
        ntype = 'info'
    elif status == 'approved':
        title = 'Tournament Registration Approved'
        msg = f'Your registration for {tournament.name} has been approved! Get ready to compete.'
        ntype = 'success'
    elif status == 'rejected':
        title = 'Tournament Registration Rejected'
        msg = f'Your registration for {tournament.name} was not approved.'
        ntype = 'error'
    else:
        title = 'Tournament Registration Update'
        msg = f'Your registration for {tournament.name} status: {status}'
        ntype = 'info'
    return create_notification(
        user=user,
        title=title,
        message=msg,
        notification_type=ntype,
        category='tournament',
        priority='normal',
        action_url=f'/user/tournaments/',
        action_text='View Tournaments',
        related_tournament=tournament,
    )

def notify_user_equipment_rental(user, equipment, status):
    status_msgs = {
        'reserved': f'Your rental for {equipment.name} has been reserved.',
        'rented': f'Your rental for {equipment.name} is now active. Enjoy!',
        'returned': f'Your rental for {equipment.name} has been returned successfully.',
        'cancelled': f'Your rental for {equipment.name} has been cancelled.',
        'overdue': f'Your rental for {equipment.name} is overdue. Please return it as soon as possible.',
    }
    title_map = {
        'reserved': 'Equipment Reserved',
        'rented': 'Equipment Rented',
        'returned': 'Equipment Returned',
        'cancelled': 'Equipment Rental Cancelled',
        'overdue': 'Equipment Overdue',
    }
    return create_notification(
        user=user,
        title=title_map.get(status, 'Equipment Update'),
        message=status_msgs.get(status, f'Equipment rental update for {equipment.name}.'),
        notification_type='error' if status == 'overdue' else 'success' if status in ('returned',) else 'info',
        category='equipment',
        priority='high' if status == 'overdue' else 'normal',
        action_url=f'/equipment/{equipment.id}/',
        action_text='View Equipment',
        related_equipment=equipment,
    )

def notify_user_account_update(user, message):
    return create_notification(
        user=user,
        title='Account Updated',
        message=message,
        notification_type='info',
        category='account',
        priority='normal',
    )


# ==================== STAFF / ADMIN NOTIFICATIONS ====================

def notify_staff_new_reservation(staff_user, reservation):
    return create_notification(
        user=staff_user,
        title='New Reservation',
        message=f'New reservation for {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} by {reservation.user.get_full_name() or reservation.user.username}.',
        notification_type='info',
        category='reservation',
        priority='normal',
        action_url=f'/staff/reservations/',
        action_text='View Reservations',
        related_reservation=reservation,
    )

def notify_staff_new_payment(staff_user, payment):
    return create_notification(
        user=staff_user,
        title='New Payment',
        message=f'Payment of ₱{payment.amount} received from {payment.reservation.user.get_full_name() or payment.reservation.user.username} for reservation #{payment.reservation.id}.',
        notification_type='success',
        category='payment',
        priority='normal',
        action_url=f'/staff/payments/',
        action_text='View Payments',
        related_payment=payment,
    )

def notify_staff_cancellation_request(staff_user, cancellation):
    res = cancellation.reservation
    return create_notification(
        user=staff_user,
        title='Cancellation Request',
        message=f'{res.user.get_full_name() or res.user.username} requested to cancel reservation for {res.court.name} on {res.date.strftime("%b %d, %Y")}.',
        notification_type='warning',
        category='cancellation',
        priority='high',
        action_url=f'/staff/cancellations/',
        action_text='Review',
        related_reservation=res,
    )

def notify_staff_tournament_registration(staff_user, registration):
    return create_notification(
        user=staff_user,
        title='New Tournament Registration',
        message=f'{registration.user.get_full_name() or registration.user.username} registered for {registration.tournament.name}.',
        notification_type='info',
        category='tournament',
        priority='normal',
        action_url=f'/admin/tournaments/',
        action_text='View Registrations',
        related_tournament=registration.tournament,
    )

def notify_staff_equipment_alert(staff_user, equipment, alert_type='low_stock'):
    alerts = {
        'low_stock': f'{equipment.name} is running low on stock.',
        'damaged': f'{equipment.name} has been reported as damaged.',
        'returned': f'{equipment.name} has been returned and is ready for inspection.',
    }
    return create_notification(
        user=staff_user,
        title='Equipment Alert',
        message=alerts.get(alert_type, f'Update for {equipment.name}.'),
        notification_type='warning' if alert_type == 'damaged' else 'info',
        category='equipment',
        priority='high' if alert_type == 'damaged' else 'normal',
        action_url=f'/staff/equipment/',
        action_text='Manage Equipment',
        related_equipment=equipment,
    )

def notify_staff_announcement(staff_user, title, message):
    return create_notification(
        user=staff_user,
        title=title,
        message=message,
        notification_type='info',
        category='announcement',
        priority='normal',
    )


# ==================== STAFF ASSIGNMENT NOTIFICATIONS ====================

def notify_staff_assigned_reservation(staff_user, reservation):
    return create_notification(
        user=staff_user,
        title='Reservation Assigned',
        message=f'Reservation for {reservation.court.name} on {reservation.date.strftime("%b %d, %Y")} has been assigned to you.',
        notification_type='info',
        category='reservation',
        priority='normal',
        action_url=f'/staff/reservations/',
        action_text='View',
        related_reservation=reservation,
    )

def notify_staff_payment_verification(staff_user, payment):
    return create_notification(
        user=staff_user,
        title='Payment Needs Verification',
        message=f'A payment of ₱{payment.amount} from {payment.reservation.user.get_full_name() or payment.reservation.user.username} needs verification.',
        notification_type='warning',
        category='payment',
        priority='high',
        action_url=f'/staff/payments/',
        action_text='Verify Payment',
        related_payment=payment,
    )

def notify_staff_equipment_update(staff_user, equipment, status):
    return create_notification(
        user=staff_user,
        title='Equipment Update',
        message=f'{equipment.name} status changed to: {status}.',
        notification_type='info',
        category='equipment',
        priority='normal',
        action_url=f'/staff/equipment/',
        action_text='View',
        related_equipment=equipment,
    )

def notify_staff_task(staff_user, task_title, task_description=''):
    return create_notification(
        user=staff_user,
        title=task_title,
        message=task_description or 'A new task has been assigned to you.',
        notification_type='info',
        category='staff',
        priority='normal',
    )


# ==================== SUPER ADMIN NOTIFICATIONS ====================

def notify_super_admin_new_payment(super_admin, payment):
    return create_notification(
        user=super_admin,
        title='New Payment',
        message=f'Payment of ₱{payment.amount} received from {payment.reservation.user.get_full_name() or payment.reservation.user.username} for reservation #{payment.reservation.id}.',
        notification_type='success',
        category='payment',
        priority='normal',
        action_url=f'/admin/payments/',
        action_text='View Payments',
        related_payment=payment,
    )

def notify_super_admin_system_error(super_admin, error_message):
    return create_notification(
        user=super_admin,
        title='System Error',
        message=f'System error detected: {error_message[:200]}',
        notification_type='error',
        category='system',
        priority='urgent',
    )

def notify_super_admin_failed_login(super_admin, username):
    return create_notification(
        user=super_admin,
        title='Failed Login Attempt',
        message=f'A failed login attempt was detected for username: {username}.',
        notification_type='warning',
        category='security',
        priority='high',
    )

def notify_super_admin_maintenance(super_admin, maintenance_info):
    return create_notification(
        user=super_admin,
        title='Scheduled Maintenance',
        message=maintenance_info,
        notification_type='warning',
        category='maintenance',
        priority='urgent',
    )

def notify_super_admin_security_alert(super_admin, alert_message):
    return create_notification(
        user=super_admin,
        title='Security Alert',
        message=alert_message[:200],
        notification_type='error',
        category='security',
        priority='urgent',
    )

def notify_super_admin_announcement(super_admin, title, message):
    return create_notification(
        user=super_admin,
        title=title,
        message=message,
        notification_type='info',
        category='announcement',
        priority='normal',
    )
