from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime

from accounts.decorators import admin_required, super_admin_required
from accounts.models import User
from .models import Notification, NotificationPreference, BroadcastMessage, NotificationTemplate, SmtpConfiguration, EmailLog
from .utils import broadcast_to_users, _get_notification_url_name


@login_required
def notification_list_view(request):
    """Modern notification list with stats, search, filter, sort, and grouping."""
    base_qs = Notification.objects.filter(
        user=request.user, is_deleted=False
    )

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        base_qs = base_qs.filter(
            Q(title__icontains=search_query) | Q(message__icontains=search_query)
        )

    # Filters
    type_filter = request.GET.get('type', '')
    if type_filter:
        base_qs = base_qs.filter(notification_type=type_filter)

    category_filter = request.GET.get('category', '')
    if category_filter:
        base_qs = base_qs.filter(category=category_filter)

    status_filter = request.GET.get('status', '')
    if status_filter == 'unread':
        base_qs = base_qs.filter(is_read=False)
    elif status_filter == 'read':
        base_qs = base_qs.filter(is_read=True)

    archive_filter = request.GET.get('archive', '')
    if archive_filter == 'archived':
        base_qs = base_qs.filter(is_archived=True)
    else:
        base_qs = base_qs.filter(is_archived=False)

    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        base_qs = base_qs.filter(priority=priority_filter)

    date_filter = request.GET.get('date', '')
    today = timezone.now().date()
    if date_filter == 'today':
        base_qs = base_qs.filter(created_at__date=today)
    elif date_filter == 'yesterday':
        base_qs = base_qs.filter(created_at__date=today - timezone.timedelta(days=1))
    elif date_filter == 'week':
        base_qs = base_qs.filter(created_at__date__gte=today - timezone.timedelta(days=7))
    elif date_filter == 'month':
        base_qs = base_qs.filter(created_at__date__gte=today - timezone.timedelta(days=30))

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sorts = ['created_at', '-created_at', 'priority', '-priority',
                     'category', '-category', 'notification_type', '-notification_type']
    if sort_by not in allowed_sorts:
        sort_by = '-created_at'
    base_qs = base_qs.order_by(sort_by)

    # Stats
    total_all = Notification.objects.filter(user=request.user, is_deleted=False).count()
    total_unread = Notification.objects.filter(user=request.user, is_read=False, is_deleted=False, is_archived=False).count()
    total_read = Notification.objects.filter(user=request.user, is_read=True, is_deleted=False).count()
    total_today = Notification.objects.filter(user=request.user, created_at__date=today, is_deleted=False).count()

    # Category counts for sidebar
    category_counts = Notification.objects.filter(
        user=request.user, is_deleted=False, is_archived=False
    ).values('category').annotate(count=Count('id')).order_by('-count')

    # Pagination
    paginator = Paginator(base_qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'archive_filter': archive_filter,
        'priority_filter': priority_filter,
        'date_filter': date_filter,
        'sort_by': sort_by,
        'total_count': total_all,
        'unread_count': total_unread,
        'read_count': total_read,
        'today_count': total_today,
        'category_counts': category_counts,
    }

    return render(request, 'user/notifications/notification_list.html', context)


@login_required
def notification_detail_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    if not notification.is_read:
        notification.mark_as_read()
    return render(request, 'user/notifications/notification_detail.html', {
        'notification': notification
    })


@login_required
def mark_notification_read_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Notification marked as read.')
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def mark_notification_unread_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_unread()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Notification marked as unread.')
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def mark_all_read_view(request):
    count = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'count': count})
    messages.success(request, f'{count} notification(s) marked as read.')
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def delete_notification_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_deleted = True
    notification.save(update_fields=['is_deleted'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Notification deleted.')
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def delete_selected_notifications_view(request):
    if request.method == 'POST':
        ids = request.POST.getlist('notification_ids')
        if ids:
            count = Notification.objects.filter(id__in=ids, user=request.user).update(is_deleted=True)
            messages.success(request, f'{count} notification(s) deleted.')
        return redirect(_get_notification_url_name(request, 'notification_list'))
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def clear_all_notifications_view(request):
    if request.method == 'POST':
        count = Notification.objects.filter(user=request.user, is_deleted=False).update(is_deleted=True)
        messages.success(request, f'Cleared {count} notification(s).')
        return redirect(_get_notification_url_name(request, 'notification_list'))
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def archive_notification_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.archive()
    messages.success(request, 'Notification archived.')
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def restore_notification_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.restore()
    messages.success(request, 'Notification restored.')
    return redirect(_get_notification_url_name(request, 'notification_list'))


@login_required
def notification_preferences_view(request):
    prefs, created = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        prefs.notify_reservation = request.POST.get('notify_reservation') == 'on'
        prefs.notify_payment = request.POST.get('notify_payment') == 'on'
        prefs.notify_refund = request.POST.get('notify_refund') == 'on'
        prefs.notify_cancellation = request.POST.get('notify_cancellation') == 'on'
        prefs.notify_tournament = request.POST.get('notify_tournament') == 'on'
        prefs.notify_equipment = request.POST.get('notify_equipment') == 'on'
        prefs.notify_staff = request.POST.get('notify_staff') == 'on'
        prefs.notify_user = request.POST.get('notify_user') == 'on'
        prefs.notify_report = request.POST.get('notify_report') == 'on'
        prefs.notify_system = request.POST.get('notify_system') == 'on'
        prefs.notify_security = request.POST.get('notify_security') == 'on'
        prefs.notify_maintenance = request.POST.get('notify_maintenance') == 'on'
        prefs.notify_announcement = request.POST.get('notify_announcement') == 'on'
        prefs.notify_promotion = request.POST.get('notify_promotion') == 'on'
        prefs.notify_message = request.POST.get('notify_message') == 'on'
        prefs.notify_account = request.POST.get('notify_account') == 'on'

        prefs.email_notifications = request.POST.get('email_notifications') == 'on'
        prefs.push_notifications = request.POST.get('push_notifications') == 'on'
        prefs.sms_notifications = request.POST.get('sms_notifications') == 'on'
        prefs.in_app_notifications = request.POST.get('in_app_notifications') == 'on'

        prefs.frequency = request.POST.get('frequency', 'instant')

        start = request.POST.get('quiet_hours_start')
        end = request.POST.get('quiet_hours_end')
        if start and end:
            prefs.quiet_hours_start = datetime.strptime(start, '%H:%M').time()
            prefs.quiet_hours_end = datetime.strptime(end, '%H:%M').time()
        else:
            prefs.quiet_hours_start = None
            prefs.quiet_hours_end = None

        prefs.save()
        messages.success(request, 'Notification preferences updated!')
        return redirect(_get_notification_url_name(request, 'notification_preferences'))

    return render(request, 'user/notifications/notification_preferences.html', {'prefs': prefs})


@login_required
def get_unread_count_api(request):
    count = Notification.objects.filter(
        user=request.user, is_read=False, is_deleted=False, is_archived=False
    ).count()

    recent = Notification.objects.filter(
        user=request.user, is_deleted=False, is_archived=False
    ).order_by('-created_at')[:5]

    data = {
        'unread_count': count,
        'recent': [{
            'id': n.id,
            'title': n.title,
            'message': n.message[:80],
            'type': n.notification_type,
            'category': n.category,
            'time': n.time_display,
            'is_read': n.is_read,
            'action_url': n.action_url or '',
            'category_color': n.category_color,
            'icon_class': n.icon_class,
        } for n in recent]
    }
    return JsonResponse(data)


# ==================== BROADCAST MANAGEMENT (Super Admin / Org Admin) ====================

@login_required
@super_admin_required
def broadcast_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        target_type = request.POST.get('target_type', 'all')
        target_roles = request.POST.getlist('target_roles')
        priority = request.POST.get('priority', 'normal')
        category = request.POST.get('category', 'announcement')
        notification_type = request.POST.get('notification_type', 'info')

        users = User.objects.filter(is_active=True)

        if target_type == 'roles' and target_roles:
            users = users.filter(role__in=target_roles)

        broadcast = BroadcastMessage.objects.create(
            title=title,
            message=message,
            sent_by=request.user,
            target_roles=target_roles,
            target_type=target_type,
            priority=priority,
            category=category,
            notification_type=notification_type,
            status='sent',
            recipient_count=users.count(),
        )

        sent = broadcast_to_users(
            users, title, message,
            notification_type=notification_type,
            category=category,
            priority=priority,
        )

        messages.success(request, f'Broadcast sent to {len(sent)} users.')
        return redirect('super_admin_broadcast_list')

    return render(request, 'staff/notifications/broadcast_create.html')


@login_required
@super_admin_required
def broadcast_list_view(request):
    broadcasts = BroadcastMessage.objects.all().order_by('-sent_at')
    return render(request, 'staff/notifications/broadcast_list.html', {
        'broadcasts': broadcasts
    })


@login_required
@super_admin_required
def broadcast_detail_view(request, broadcast_id):
    broadcast = get_object_or_404(BroadcastMessage, id=broadcast_id)
    return render(request, 'staff/notifications/broadcast_detail.html', {
        'broadcast': broadcast
    })


@login_required
def get_broadcast_stats_api(request):
    total_sent = BroadcastMessage.objects.filter(sent_by=request.user).aggregate(
        total=Sum('recipient_count')
    )['total'] or 0
    total_broadcasts = BroadcastMessage.objects.filter(sent_by=request.user).count()
    return JsonResponse({
        'total_sent': total_sent,
        'total_broadcasts': total_broadcasts,
    })


# ==================== SMTP MANAGEMENT (Super Admin) ====================

@login_required
@super_admin_required
def smtp_settings_view(request):
    """View and edit SMTP configuration."""
    from .email_service import get_smtp_config

    config = SmtpConfiguration.objects.filter(is_active=True).first()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'toggle':
            if config:
                config.status = 'disabled' if config.status == 'enabled' else 'enabled'
                config.updated_by = request.user
                config.save()
                messages.success(request, f'SMTP configuration {"enabled" if config.status == "enabled" else "disabled"}.')
            return redirect('super_admin_smtp_settings')

        # Save SMTP settings
        smtp_host = request.POST.get('smtp_host', '').strip()
        smtp_port = request.POST.get('smtp_port', '587')
        smtp_username = request.POST.get('smtp_username', '').strip()
        smtp_password = request.POST.get('smtp_password', '').strip()
        encryption = request.POST.get('encryption', 'tls')
        sender_name = request.POST.get('sender_name', 'PickleSphere').strip()
        sender_email = request.POST.get('sender_email', 'noreply@picklesphere.com').strip()
        smtp_status = request.POST.get('status', 'enabled')

        if not smtp_host:
            messages.error(request, 'SMTP Host is required.')
            return render(request, 'staff/notifications/smtp_settings.html', {'config': config})

        if not sender_email:
            messages.error(request, 'Sender Email is required.')
            return render(request, 'staff/notifications/smtp_settings.html', {'config': config})

        try:
            smtp_port = int(smtp_port)
        except (ValueError, TypeError):
            messages.error(request, 'SMTP Port must be a number.')
            return render(request, 'staff/notifications/smtp_settings.html', {'config': config})

        if config:
            config.smtp_host = smtp_host
            config.smtp_port = smtp_port
            config.smtp_username = smtp_username
            if smtp_password:
                config.smtp_password = smtp_password
            config.encryption = encryption
            config.sender_name = sender_name
            config.sender_email = sender_email
            config.status = smtp_status
            config.updated_by = request.user
            config.save()
        else:
            config = SmtpConfiguration.objects.create(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                encryption=encryption,
                sender_name=sender_name,
                sender_email=sender_email,
                status=smtp_status,
                updated_by=request.user,
            )

        messages.success(request, 'SMTP settings saved successfully!')
        return redirect('super_admin_smtp_settings')

    # Get current SMTP settings from env as fallback info
    env_config = get_smtp_config()

    return render(request, 'staff/notifications/smtp_settings.html', {
        'config': config,
        'env_config': env_config,
    })


@login_required
@super_admin_required
def smtp_test_email_view(request):
    """Send a test email to verify SMTP configuration."""
    if request.method == 'POST':
        test_email = request.POST.get('test_email', '').strip()

        if not test_email:
            messages.error(request, 'Please provide an email address to send the test to.')
            return redirect('super_admin_smtp_settings')

        from .email_utils import send_test_email

        # Use a dummy user object for the test
        class DummyUser:
            email = test_email
            username = 'Test User'
            get_full_name = lambda self: 'Test User'

        dummy = DummyUser()

        try:
            # Try to find an actual user with this email
            actual_user = User.objects.filter(email=test_email).first()
            if actual_user:
                success = send_test_email(actual_user)
            else:
                from .email_service import send_email
                success = send_email(
                    recipient_email=test_email,
                    subject='Test Email from PickleSphere',
                    html_template='emails/test_email.html',
                    context={
                        'title': 'Test Email',
                        'message': 'If you received this email, your SMTP configuration is working correctly!',
                        'user': dummy,
                    },
                    email_type='test',
                )

            if success:
                messages.success(request, f'Test email sent successfully to {test_email}!')
            else:
                messages.error(request, 'Failed to send test email. Please check your SMTP settings and try again.')
        except Exception as e:
            messages.error(request, f'Error sending test email: {str(e)}')

        return redirect('super_admin_smtp_settings')

    return redirect('super_admin_smtp_settings')


@login_required
@super_admin_required
def email_log_list_view(request):
    """View email logs for auditing and debugging."""
    logs = EmailLog.objects.all().order_by('-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        logs = logs.filter(status=status_filter)

    email_type_filter = request.GET.get('email_type', '')
    if email_type_filter:
        logs = logs.filter(email_type=email_type_filter)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        logs = logs.filter(
            Q(recipient__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(email_type__icontains=search_query)
        )

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    # Stats
    total_sent = EmailLog.objects.filter(status='sent').count()
    total_failed = EmailLog.objects.filter(status='failed').count()
    total_pending = EmailLog.objects.filter(status='pending').count()
    total_all = EmailLog.objects.count()

    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'staff/notifications/email_log_list.html', {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'email_type_filter': email_type_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_sent': total_sent,
        'total_failed': total_failed,
        'total_pending': total_pending,
        'total_all': total_all,
    })


@login_required
@super_admin_required
def email_log_detail_view(request, log_id):
    """View a single email log entry."""
    log = get_object_or_404(EmailLog, id=log_id)
    return render(request, 'staff/notifications/email_log_detail.html', {
        'log': log,
    })
