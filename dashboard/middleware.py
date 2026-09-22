"""
Middleware modules for the PickleSphere dashboard app.

Contains:
- MaintenanceModeMiddleware: Blocks non-admin users when maintenance is active.
- AuthAuditMiddleware: Development-only audit of unauthenticated access patterns.
"""

import logging

from django.shortcuts import render
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.urls import resolve, Resolver404

from .cache_utils import record_slow_query

logger = logging.getLogger('picklesphere.auth_audit')


class MaintenanceModeMiddleware:
    """Middleware that checks maintenance mode and blocks non-admin users.
    Uses caching to avoid a database hit on every request."""

    CACHE_KEY = 'maintenance_mode_data'
    CACHE_TIMEOUT = 30  # seconds — short enough to pick up changes quickly

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip maintenance check for static/media files and admin page
        path = request.path_info
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Check cache first to avoid DB hit on every request
        data = cache.get(self.CACHE_KEY)

        if data is None:
            # Cache miss — query the database
            from .models import MaintenanceMode
            try:
                maint = MaintenanceMode.objects.get(pk=1)
                data = {
                    'is_active': maint.is_active,
                    'scheduled_end': maint.scheduled_end.isoformat() if maint.scheduled_end else None,
                    'title': maint.title,
                    'message': maint.message,
                    'banner_image_url': maint.banner_image.url if maint.banner_image else None,
                    'estimated_return': maint.estimated_return.isoformat() if maint.estimated_return else None,
                    'show_contact_info': maint.show_contact_info,
                    'contact_email': maint.contact_email,
                    'contact_phone': maint.contact_phone,
                    'scheduled_start': maint.scheduled_start.isoformat() if maint.scheduled_start else None,
                }
            except MaintenanceMode.DoesNotExist:
                data = {'is_active': False}
            # Cache the result so subsequent requests skip the DB
            cache.set(self.CACHE_KEY, data, self.CACHE_TIMEOUT)

        # Auto-disable if scheduled end has passed (need DB for this write)
        if data.get('is_active') and data.get('scheduled_end'):
            scheduled_end = timezone.datetime.fromisoformat(data['scheduled_end'])
            if scheduled_end.tzinfo is None:
                scheduled_end = timezone.make_aware(scheduled_end)
            if timezone.now() >= scheduled_end:
                # Need DB access for the write — this is rare
                from .models import MaintenanceMode
                try:
                    maint = MaintenanceMode.objects.get(pk=1)
                    maint.is_active = False
                    maint.last_disabled_at = timezone.now()
                    maint.save(update_fields=['is_active', 'last_disabled_at'])
                    # Invalidate cache
                    cache.delete(self.CACHE_KEY)

                    from .models import MaintenanceAuditLog
                    MaintenanceAuditLog.objects.create(
                        action='auto_disabled',
                        details='Auto-disabled because scheduled end time was reached.',
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                except MaintenanceMode.DoesNotExist:
                    pass
                return self.get_response(request)

        # If maintenance is NOT active, proceed normally
        if not data.get('is_active'):
            return self.get_response(request)

        # If maintenance IS active, allow super admins through
        if request.user.is_authenticated and request.user.is_super_admin():
            return self.get_response(request)

        # Also allow login page so super admins can log in
        if path.startswith('/accounts/login/') or path.startswith('/accounts/logout/'):
            return self.get_response(request)

        # Show maintenance page for everyone else
        return render(request, 'maintenance.html', {
            'maintenance': data,
            'page_title': 'System Under Maintenance',
        })


class SlowQueryMiddleware:
    """Records slow database queries for the Cache Monitor page.

    Only active when DEBUG is on or CACHE_MONITOR_ENABLED is set. Uses the
    Django connection's query log (which is only populated when the debug
    cursor is forced on, so production must opt in via CACHE_MONITOR_ENABLED).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.threshold_ms = getattr(settings, 'SLOW_QUERY_THRESHOLD_MS', 150)

    def __call__(self, request):
        response = self.get_response(request)
        if not getattr(settings, 'CACHE_MONITOR_ENABLED', False):
            return response
        try:
            from django.db import connection
            if not connection.queries:
                return response
            for q in connection.queries:
                duration_ms = float(q.get('time', 0)) * 1000
                if duration_ms >= self.threshold_ms:
                    record_slow_query(duration_ms, q.get('sql', ''))
        except Exception:
            pass
        return response


class AuthAuditMiddleware:
    """
    Development middleware that logs warnings when unauthenticated users
    access views that might be missing @login_required protection.

    How it works:
    --------
    1. Before the view runs, records the request path and resolved URL name.
    2. After the response is generated, checks the outcome:
       - If response is a 302 redirect to LOGIN_URL → the view IS protected.
         Logged at INFO level (confirms protection is working).
       - If response is 200 and view is not on the public-allowlist →
         the view MIGHT be unprotected. Logged at WARNING level.

    Only active when DEBUG=True. No performance impact in production.
    """

    # URL names of views that are intentionally public.
    # Add any new public views here to avoid false warnings.
    PUBLIC_URL_NAMES = frozenset({
        # Dashboard public pages
        'home',
        'court_view',
        'pricing',
        'about',
        'contact',
        'privacy_policy',
        'terms_of_service',
        'faq',
        # Auth pages
        'login',
        'register',
        'password_reset_request',
        'password_reset_confirm',
        # Tournaments public pages
        'tournament_list',
        'tournament_detail',
        # Courts public views
        'court_detail',
        'court_list',
        'court_availability',
        'all_courts',
    })

    # Path prefixes that are always public (bypass URL resolution)
    PUBLIC_PATH_PREFIXES = (
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only active in DEBUG mode — no overhead in production
        if not settings.DEBUG:
            return self.get_response(request)

        # If user is authenticated, nothing to audit
        if request.user.is_authenticated:
            return self.get_response(request)

        # Skip known public path prefixes (static/media)
        path = request.path_info
        if path.startswith(self.PUBLIC_PATH_PREFIXES):
            return self.get_response(request)

        # Resolve the URL name for better logging
        url_name = None
        try:
            match = resolve(path)
            url_name = match.url_name
        except Resolver404:
            url_name = None

        # If the URL name is in the public allowlist, skip silently
        if url_name and url_name in self.PUBLIC_URL_NAMES:
            return self.get_response(request)

        # ---- Process the request ----
        response = self.get_response(request)

        # ---- Analyze the response ----
        login_url = settings.LOGIN_URL  # e.g., '/accounts/login/'

        if response.status_code == 302:
            redirect_location = response.get('Location', '')
            if redirect_location.startswith(login_url):
                # View IS protected — redirected to login. Log at INFO.
                logger.info(
                    '[AUTH_AUDIT] ✅ Protected view → login redirect | '
                    'path=%(path)s url_name=%(url_name)s method=%(method)s',
                    {
                        'path': path,
                        'url_name': url_name,
                        'method': request.method,
                    },
                )
            else:
                # Redirect elsewhere — might be a public view doing its own redirect
                logger.debug(
                    '[AUTH_AUDIT] Unauthenticated user redirected to %(location)s | '
                    'path=%(path)s url_name=%(url_name)s',
                    {
                        'location': redirect_location,
                        'path': path,
                        'url_name': url_name,
                    },
                )

        elif response.status_code == 200:
            # View returned a 200 OK to an unauthenticated user.
            # This view is NOT in the public allowlist — it might need @login_required.
            extra = {
                'path': path,
                'url_name': url_name,
                'method': request.method,
                'ip': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:120],
                'referrer': request.META.get('HTTP_REFERER', '')[:200],
            }

            logger.warning(
                '[AUTH_AUDIT] ⚠️  POTENTIALLY UNPROTECTED VIEW | '
                'path=%(path)s url_name=%(url_name)s method=%(method)s ip=%(ip)s',
                extra,
                extra={'audit_data': extra},
            )

        return response
