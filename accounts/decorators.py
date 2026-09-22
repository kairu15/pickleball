from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def super_admin_required(view_func):
    """
    Decorator that restricts access to Super Admin users only.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')
        if not request.user.is_super_admin():
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_or_admin_required(view_func):
    """
    Decorator that restricts access to staff or admin users
    (Super Admin or Staff role).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')
        if not request.user.is_staff_user():
            messages.error(request, 'You do not have permission to access this page.')
            if request.user.is_normal_user():
                return redirect('user_dashboard')
            # Fallback for any other non-staff role
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator that restricts access to admin-level users (Super Admin).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')
        if not request.user.is_admin():
            messages.error(request, 'You do not have permission to access this page.')
            if request.user.is_staff_member():
                return redirect('staff_dashboard')
            return redirect('user_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def user_required(view_func):
    """
    Decorator that restricts access to regular users only.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')
        if not request.user.is_normal_user():
            messages.error(request, 'You do not have permission to access this page.')
            # Redirect through the role-based dashboard dispatcher to avoid redirect loops
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
