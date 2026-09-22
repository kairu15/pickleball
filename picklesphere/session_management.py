"""
Session Management Module for PickleSphere
Handles session tracking, timeout warnings, and security features
"""

import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import logout
from django.http import JsonResponse


class EnhancedSessionMiddleware(SessionMiddleware):
    """
    Enhanced session middleware that tracks user activity,
    handles session timeouts, and provides security features.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        # Session timeout in seconds (default: 30 minutes)
        self.session_timeout = getattr(settings, 'SESSION_TIMEOUT', 1800)
        # Warning before timeout in seconds (default: 5 minutes)
        self.warning_before = getattr(settings, 'SESSION_WARNING_BEFORE', 300)
    
    def __call__(self, request):
        # Process request - check session validity
        self._process_request_session(request)
        
        # Call the view
        response = self.get_response(request)
        
        # Process response - update session data
        self._process_response_session(request, response)
        
        return response
    
    def _process_request_session(self, request):
        """Process session on request - check for timeout and track activity"""
        if not hasattr(request, 'session'):
            return
        
        # Skip for certain paths (static files, login, etc.)
        path = request.path_info
        skip_paths = [
            '/static/', '/media/', '/accounts/login/', '/accounts/register/',
            '/accounts/logout/', '/api/session/heartbeat/',
        ]
        if any(path.startswith(skip) for skip in skip_paths):
            return
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            now = timezone.now()
            
            # Get last activity timestamp
            last_activity = request.session.get('last_activity')
            if last_activity:
                try:
                    last_activity = datetime.fromisoformat(last_activity)
                    # Check for session timeout
                    elapsed = (now - last_activity).total_seconds()
                    
                    if elapsed > self.session_timeout:
                        # Session expired - logout user
                        self._handle_session_timeout(request)
                        return
                    
                    # Calculate time remaining
                    time_remaining = self.session_timeout - elapsed
                    request.session['time_remaining'] = time_remaining
                    
                    # Check if warning should be shown
                    if time_remaining <= self.warning_before:
                        request.session['show_timeout_warning'] = True
                    else:
                        request.session['show_timeout_warning'] = False
                        
                except (ValueError, TypeError):
                    pass
            
            # Update activity tracking
            request.session['last_activity'] = now.isoformat()
            
            # Track page views for analytics
            self._track_page_view(request)
    
    def _process_response_session(self, request, response):
        """Process session on response - add headers and save data"""
        if not hasattr(request, 'session'):
            return response
        
        # Add security headers
        response['X-Session-Active'] = 'true' if request.user.is_authenticated else 'false'
        
        # Add timeout warning header if needed
        if request.session.get('show_timeout_warning'):
            response['X-Session-Warning'] = 'true'
            response['X-Session-Time-Remaining'] = str(int(request.session.get('time_remaining', 0)))
        
        return response
    
    def _handle_session_timeout(self, request):
        """Handle session timeout by logging out the user"""
        # Log the timeout event
        if hasattr(request, 'user') and request.user.is_authenticated:
            from accounts.models import UserActivity
            UserActivity.objects.create(
                user=request.user,
                action='Session Timeout',
                details='User session expired due to inactivity'
            )
        
        # Clear session data but preserve messages
        messages = request.session.get('_messages', [])
        request.session.flush()
        
        # Restore messages
        if messages:
            request.session['_messages'] = messages
        
        # Mark session as expired
        request.session['session_expired'] = True
        request.session['expired_at'] = timezone.now().isoformat()
    
    def _track_page_view(self, request):
        """Track page views for user analytics"""
        # Initialize session tracking data
        if 'page_views' not in request.session:
            request.session['page_views'] = 0
            request.session['session_start'] = timezone.now().isoformat()
        
        # Increment page view counter
        request.session['page_views'] = request.session.get('page_views', 0) + 1
        request.session['last_page'] = request.path_info


class SessionActivityMiddleware:
    """
    Middleware to track detailed user activity in sessions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Track activity before processing
        if request.user.is_authenticated:
            self._record_activity(request)
        
        response = self.get_response(request)
        
        return response
    
    def _record_activity(self, request):
        """Record user activity in session"""
        if not hasattr(request, 'session'):
            return
        
        now = timezone.now()
        
        # Initialize activity log
        if 'activity_log' not in request.session:
            request.session['activity_log'] = []
        
        # Get recent activity
        activity_log = request.session['activity_log']
        
        # Add current activity
        current_activity = {
            'timestamp': now.isoformat(),
            'path': request.path_info,
            'method': request.method,
        }
        
        # Keep only last 20 activities
        activity_log.append(current_activity)
        request.session['activity_log'] = activity_log[-20:]
        
        # Update session metadata
        request.session['total_requests'] = request.session.get('total_requests', 0) + 1
        request.session['last_request'] = now.isoformat()


def get_session_info(request):
    """
    Get comprehensive session information for the current user
    """
    if not request.user.is_authenticated:
        return {
            'active': False,
            'expires_at': None,
            'time_remaining': 0,
        }
    
    session = request.session
    now = timezone.now()
    
    # Calculate session info
    last_activity = session.get('last_activity')
    session_start = session.get('session_start')
    timeout = getattr(settings, 'SESSION_TIMEOUT', 1800)
    
    if last_activity:
        try:
            last_activity_dt = datetime.fromisoformat(last_activity)
            expires_at = last_activity_dt + timedelta(seconds=timeout)
            time_remaining = max(0, (expires_at - now).total_seconds())
        except (ValueError, TypeError):
            expires_at = now + timedelta(seconds=timeout)
            time_remaining = timeout
    else:
        expires_at = now + timedelta(seconds=timeout)
        time_remaining = timeout
    
    return {
        'active': True,
        'session_key': session.session_key[:8] + '...' if session.session_key else None,
        'session_start': session_start,
        'last_activity': last_activity,
        'expires_at': expires_at.isoformat() if expires_at else None,
        'time_remaining': int(time_remaining),
        'time_remaining_formatted': format_duration(time_remaining),
        'page_views': session.get('page_views', 0),
        'total_requests': session.get('total_requests', 0),
        'warning_threshold': getattr(settings, 'SESSION_WARNING_BEFORE', 300),
        'show_warning': time_remaining <= getattr(settings, 'SESSION_WARNING_BEFORE', 300),
    }


def format_duration(seconds):
    """Format seconds into human readable duration"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def session_context_processor(request):
    """
    Context processor to make session information available in all templates
    """
    return {
        'session_info': get_session_info(request),
        'session_warning_seconds': getattr(settings, 'SESSION_WARNING_BEFORE', 300),
        'session_timeout_seconds': getattr(settings, 'SESSION_TIMEOUT', 1800),
    }
