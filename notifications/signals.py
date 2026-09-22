from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_login_failed
from django.utils import timezone
from django.core.cache import caches

from .models import Notification
from .utils import (
    create_notification,
    notify_user_reservation_submitted,
    notify_user_reservation_confirmed,
    notify_user_reservation_rejected,
    notify_user_reservation_cancelled,
    notify_user_reservation_completed,
    notify_user_payment_confirmed,
    notify_user_refund_processed,
    notify_user_tournament_registration,
    notify_user_equipment_rental,
    notify_user_account_update,
    notify_staff_new_reservation,
    notify_staff_new_payment,
    notify_staff_cancellation_request,
    notify_staff_tournament_registration,
    notify_staff_equipment_update,
    notify_staff_payment_verification,
    notify_super_admin_new_payment,
    notify_super_admin_failed_login,
    notify_super_admin_security_alert,
)
from accounts.models import User


# ==================== NOTIFICATION CACHE INVALIDATION ====================

@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def notification_cache_invalidate(sender, instance, **kwargs):
    """Invalidate the per-user notification badge cache when a notification is
    created, marked read, or deleted so the navbar bell stays accurate."""
    try:
        caches['pages'].delete(f'user_notifs_{instance.user_id}')
        caches['pages'].delete(f'user_badges_{instance.user_id}')
    except Exception:
        pass


# ==================== RESERVATION SIGNALS ====================

@receiver(post_save, sender='reservations.Reservation')
def reservation_saved_handler(sender, instance, created, **kwargs):
    try:
        user = instance.user
        if created:
            notify_user_reservation_submitted(user, instance)
            # Notify all active staff members of the new reservation
            staff_users = User.objects.filter(role='staff', is_active=True)
            for staff in staff_users:
                notify_staff_new_reservation(staff, instance)
            return

        if hasattr(instance, '_old_status'):
            old_status = instance._old_status
            new_status = instance.status
            if old_status != new_status:
                if new_status == 'confirmed':
                    notify_user_reservation_confirmed(user, instance)
                elif new_status == 'cancelled':
                    notify_user_reservation_cancelled(user, instance)
                elif new_status == 'rejected':
                    notify_user_reservation_rejected(user, instance)
                elif new_status == 'completed':
                    notify_user_reservation_completed(user, instance)
    except Exception:
        pass


@receiver(pre_save, sender='reservations.Reservation')
def reservation_pre_save_handler(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# ==================== PAYMENT SIGNALS ====================

@receiver(post_save, sender='payments.Payment')
def payment_saved_handler(sender, instance, created, **kwargs):
    try:
        user = instance.reservation.user if instance.reservation else None
        if not user:
            return
        if created:
            notify_user_payment_confirmed(user, instance)
            # Notify staff of the new payment for verification
            staff_users = User.objects.filter(role='staff', is_active=True)
            for staff in staff_users:
                notify_staff_new_payment(staff, instance)
            # Notify super admins of the payment
            super_admins = User.objects.filter(role='super_admin', is_active=True)
            for admin in super_admins:
                notify_super_admin_new_payment(admin, instance)
            return
        if hasattr(instance, '_old_status'):
            new_status = instance.status
            if new_status == 'pending' and instance.method in ('gcash', 'maya', 'bank_transfer'):
                staff_users = User.objects.filter(role='staff', is_active=True)
                for staff in staff_users:
                    notify_staff_payment_verification(staff, instance)
    except Exception:
        pass


@receiver(pre_save, sender='payments.Payment')
def payment_pre_save_handler(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# ==================== CANCELLATION SIGNALS ====================

@receiver(post_save, sender='reservations.CancellationRequest')
def cancellation_request_handler(sender, instance, created, **kwargs):
    try:
        if created:
            # Notify all active staff members of the cancellation request
            staff_users = User.objects.filter(role='staff', is_active=True)
            for staff in staff_users:
                notify_staff_cancellation_request(staff, instance)
        if instance.approved and instance.refund_processed:
            notify_user_refund_processed(instance.reservation.user, instance)
    except Exception:
        pass


# ==================== TOURNAMENT SIGNALS ====================

@receiver(post_save, sender='tournaments.Registration')
def tournament_registration_handler(sender, instance, created, **kwargs):
    try:
        status = 'pending' if instance.status == 'pending' else instance.status
        notify_user_tournament_registration(instance.user, instance.tournament, status)
        if created:
            # Notify all active staff members of the new tournament registration
            staff_users = User.objects.filter(role='staff', is_active=True)
            for staff in staff_users:
                notify_staff_tournament_registration(staff, instance)
    except Exception:
        pass


# ==================== EQUIPMENT RENTAL SIGNALS ====================

@receiver(post_save, sender='equipment.EquipmentRental')
def equipment_rental_handler(sender, instance, created, **kwargs):
    try:
        if created:
            status = 'reserved' if instance.status == 'reserved' else instance.status
        else:
            if hasattr(instance, '_old_status'):
                status = instance.status
            else:
                return
        notify_user_equipment_rental(instance.rented_by, instance.equipment, status)
        if status in ('reserved', 'rented', 'returned', 'overdue'):
            staff_users = User.objects.filter(role='staff', is_active=True)
            for staff in staff_users:
                notify_staff_equipment_update(staff, instance.equipment, status)
    except Exception:
        pass


# ==================== LOGIN / SECURITY SIGNALS ====================

@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    request.session['last_login'] = timezone.now().isoformat()


@receiver(user_login_failed)
def user_login_failed_handler(sender, credentials, request, **kwargs):
    try:
        username = credentials.get('username', '')
        if username:
            super_admins = User.objects.filter(role='super_admin', is_active=True)
            for admin in super_admins:
                notify_super_admin_failed_login(admin, username)
    except Exception:
        pass
