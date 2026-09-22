"""
Session Management API Views for PickleSphere
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings

from .session_management import get_session_info, format_duration


@require_http_methods(["POST"])
@csrf_exempt
def session_heartbeat(request):
    """
    API endpoint to keep session alive via heartbeat
    Called periodically from frontend to prevent timeout
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Not authenticated',
            'authenticated': False
        }, status=401)
    
    # Update last activity
    request.session['last_activity'] = timezone.now().isoformat()
    
    # Get updated session info
    info = get_session_info(request)
    
    return JsonResponse({
        'status': 'success',
        'authenticated': True,
        'time_remaining': info['time_remaining'],
        'time_remaining_formatted': info['time_remaining_formatted'],
        'show_warning': info['show_warning'],
    })


@login_required
def session_info(request):
    """
    API endpoint to get current session information
    """
    info = get_session_info(request)
    
    # Add additional details for debugging
    info['session_cookie_age'] = getattr(settings, 'SESSION_COOKIE_AGE', 3600)
    info['session_timeout'] = getattr(settings, 'SESSION_TIMEOUT', 1800)
    info['warning_threshold'] = getattr(settings, 'SESSION_WARNING_BEFORE', 300)
    
    return JsonResponse({
        'status': 'success',
        **info
    })


@login_required
def extend_session(request):
    """
    API endpoint to extend session timeout
    Resets the last_activity timestamp
    """
    # Reset last activity to now
    now = timezone.now()
    request.session['last_activity'] = now.isoformat()
    
    # Get updated info
    timeout = getattr(settings, 'SESSION_TIMEOUT', 1800)
    expires_at = now + timedelta(seconds=timeout)
    
    return JsonResponse({
        'status': 'success',
        'message': 'Session extended successfully',
        'expires_at': expires_at.isoformat(),
        'time_remaining': timeout,
        'time_remaining_formatted': format_duration(timeout),
    })
