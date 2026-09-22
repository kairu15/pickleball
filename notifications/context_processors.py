from django.core.cache import caches

from .models import Notification

# Cache the per-user unread count + recent notifications for a short window to
# avoid two queries on EVERY request for every authenticated user. The cache
# entry is invalidated immediately whenever a Notification for that user is
# created, read, or deleted (see notifications/signals.py).
_USER_NOTIFS_TTL = 300


def _get_user_notifications(user):
    unread_count = Notification.objects.filter(
        user=user,
        is_read=False,
        is_deleted=False,
        is_archived=False,
    ).count()
    recent_notifications = list(Notification.objects.filter(
        user=user,
        is_deleted=False,
        is_archived=False,
    ).order_by('-created_at')[:5])
    return unread_count, recent_notifications


def notification_count(request):
    """Context processor to add unread notification count and recent
    notifications to all templates (cached per user)."""
    if request.user.is_authenticated:
        try:
            cache = caches['pages']
            key = f'user_notifs_{request.user.id}'
            data = cache.get(key)
            if data is None:
                data = _get_user_notifications(request.user)
                cache.set(key, data, _USER_NOTIFS_TTL)
            unread_count, recent_notifications = data
        except Exception:
            # Cache backend unavailable - fall back to live queries
            unread_count, recent_notifications = _get_user_notifications(request.user)
        return {
            'unread_notification_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {
        'unread_notification_count': 0,
        'recent_notifications': [],
    }
