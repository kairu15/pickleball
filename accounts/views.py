import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Q, Count
from django.urls import reverse
from django.http import JsonResponse
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserProfileForm,
    UserRoleForm,
    AdminUserCreateForm,
    AdminUserUpdateForm,
    PasswordResetRequestForm,
    SetPasswordForm,
)
from .models import User, UserActivity
from .decorators import admin_required, staff_or_admin_required, user_required
from .otp_utils import (
    create_and_send_otp, verify_otp_code, cleanup_expired_otps,
    OTP_EXPIRY_MINUTES, OTP_RESEND_MAX_PER_IP, OTP_RESEND_WINDOW_MINUTES,
)
from notifications.models import Notification
from notifications.email_utils import (
    send_welcome_email,
    send_account_update_email,
    send_password_changed_email,
    send_account_suspension_email,
    send_account_reactivation_email,
    send_login_security_alert_email,
)

logger = logging.getLogger(__name__)


def password_reset_request(request):
    """Handle forgot password - send OTP to email."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email__iexact=email, is_active=True)
                ip = request.META.get('REMOTE_ADDR')
                success, otp_obj, error = create_and_send_otp(
                    email=email,
                    purpose='password_reset',
                    user=user,
                    ip_address=ip,
                    request=request,
                )
                if success:
                    # Store email in session for OTP verification
                    request.session['otp_email'] = email
                    request.session['otp_purpose'] = 'password_reset'
                    return redirect('verify_otp')
                else:
                    messages.error(request, error or 'Failed to send OTP. Please try again.')
                    return redirect('password_reset_request')
            except User.DoesNotExist:
                # Silently ignore inactive/nonexistent accounts to prevent info leakage
                pass
            messages.success(request, 'If an account exists with that email, an OTP will be sent.')
            return redirect('login')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'auth/password_reset_request.html', {'form': form})


def password_reset_confirm(request):
    """Handle password reset after OTP verification - set new password."""
    if request.user.is_authenticated:
        return redirect('home')

    # Ensure OTP was verified for password reset
    email = request.session.get('otp_email')
    otp_verified = request.session.get('otp_purpose') == 'password_reset' and request.session.get('otp_verified')
    
    if not email or not otp_verified:
        messages.error(request, 'Please verify your email first.')
        return redirect('password_reset_request')

    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        messages.error(request, 'Account not found.')
        return redirect('password_reset_request')

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            # Clear session flags
            request.session.pop('otp_email', None)
            request.session.pop('otp_purpose', None)
            request.session.pop('otp_verified', None)
            
            messages.success(request, 'Your password has been reset successfully. Please sign in.')
            return redirect('login')
    else:
        form = SetPasswordForm()

    return render(request, 'auth/password_reset_confirm.html', {
        'form': form,
        'validlink': True,
        'email': email,
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'user'
            user.is_active = False  # Deactivate until OTP is verified
            user.save()
            
            # Send OTP for email verification
            ip = request.META.get('REMOTE_ADDR')
            success, otp_obj, error = create_and_send_otp(
                email=user.email,
                purpose='registration',
                user=user,
                ip_address=ip,
                request=request,
            )
            
            if success:
                # Store registration data and email in session
                request.session['otp_email'] = user.email
                request.session['otp_purpose'] = 'registration'
                request.session['reg_user_id'] = user.id
                
                # AJAX request: return JSON for in-page modal
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'email': user.email,
                        'otp_expiry_minutes': OTP_EXPIRY_MINUTES,
                        'message': 'Account created! Please check your email for the verification code.',
                    })
                
                messages.success(
                    request,
                    'Account created! Please check your email for the verification code.'
                )
                return redirect('verify_otp')
            else:
                # OTP sending failed, delete the user and show error
                user.delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error or 'Failed to send verification email. Please try again.'
                    }, status=400)
                messages.error(request, error or 'Failed to send verification email. Please try again.')
                return redirect('register')
        else:
            # Form validation errors - return JSON for AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, field_errors in form.errors.items():
                    errors[field] = field_errors[0]
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form, 'otp_expiry_minutes': OTP_EXPIRY_MINUTES})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Log activity
            UserActivity.objects.create(
                user=user,
                action='Login',
                details=f'User logged in from {request.META.get("REMOTE_ADDR")}'
            )
            
            messages.success(request, f'Welcome back, {user.first_name}!')
            
            # Redirect based on role
            # Send login security alert for new IP addresses.
            # Never block login if the email fails to send.
            try:
                ip_address = request.META.get('REMOTE_ADDR', '')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                send_login_security_alert_email(user, ip_address, user_agent)
            except Exception as e:
                logger.warning(f'Failed to send login security alert email for {user.username}: {e}')

            if user.is_super_admin():
                return redirect('super_admin_analytics')
            elif user.is_staff_member():
                return redirect('staff_dashboard')
            else:
                return redirect('user_dashboard')
    else:
        form = UserLoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


@login_required
def logout_view(request):
    # Log activity
    UserActivity.objects.create(
        user=request.user,
        action='Logout',
        details=f'User logged out from {request.META.get("REMOTE_ADDR")}'
    )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


def _get_profile_urls(user):
    """Return dashboard_url and profile_url based on user role."""
    if user.is_super_admin():
        return {
            'dashboard_url': 'super_admin_dashboard',
            'profile_url': 'super_admin_profile',
        }
    elif user.is_staff_member():
        return {
            'dashboard_url': 'staff_dashboard',
            'profile_url': 'staff_profile',
        }
    else:
        return {
            'dashboard_url': 'user_dashboard',
            'profile_url': 'profile',
        }


@login_required
def profile_view(request):
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    
    from reservations.models import Reservation
    from tournaments.models import Registration
    from scoring.models import Match
    
    # Reservation history (last 10)
    reservation_history = Reservation.objects.filter(
        user=request.user
    ).select_related('court', 'court__site').order_by('-date', '-start_time')[:10]
    
    # Reservation stats
    total_reservations = Reservation.objects.filter(user=request.user).exclude(status='cancelled').count()
    completed_reservations = Reservation.objects.filter(user=request.user, status='completed').count()
    pending_reservations = Reservation.objects.filter(user=request.user, status='pending').count()
    cancelled_reservations = Reservation.objects.filter(user=request.user, status='cancelled').count()
    confirmed_reservations = Reservation.objects.filter(user=request.user, status='confirmed').count()
    
    # Tournament participation
    tournament_registrations = Registration.objects.filter(
        user=request.user
    ).select_related('tournament').order_by('-registered_at')[:10]
    tournament_count = tournament_registrations.count()
    
    # Match history
    match_history = Match.objects.filter(
        Q(team1_player1=request.user) | Q(team1_player2=request.user) |
        Q(team2_player1=request.user) | Q(team2_player2=request.user)
    ).select_related(
        'team1_player1', 'team1_player2', 'team2_player1', 'team2_player2'
    ).prefetch_related('games').order_by('-created_at')[:10]
    
    # Match stats
    completed_matches = Match.objects.filter(
        Q(team1_player1=request.user) | Q(team1_player2=request.user) |
        Q(team2_player1=request.user) | Q(team2_player2=request.user),
        status='completed'
    ).count()
    
    # Wins (completed matches where user's team won)
    wins = 0
    for m in match_history:
        if m.status != 'completed' or not m.winner_team:
            continue
        if (m.team1_player1 == request.user or m.team1_player2 == request.user) and m.winner_team == 1:
            wins += 1
        elif (m.team2_player1 == request.user or m.team2_player2 == request.user) and m.winner_team == 2:
            wins += 1
    
    # Favorite courts
    favorite_courts_qs = Reservation.objects.filter(
        user=request.user
    ).exclude(status='cancelled').values(
        'court__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:3]
    favorite_courts = [item['court__name'] for item in favorite_courts_qs if item['court__name']]
    
    # Recent activity (from UserActivity model)
    recent_activities = UserActivity.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Determine role-based URL names
    urls = _get_profile_urls(request.user)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                # Send profile update confirmation email
                send_account_update_email(request.user, 'Your profile has been updated successfully.')
                return redirect(urls['profile_url'])
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                # Send password changed notification
                send_password_changed_email(request.user)
                messages.success(request, 'Password changed successfully!')
                return redirect(urls['profile_url'])
            else:
                messages.error(request, 'Please correct the password errors below.')
    
    return render(request, 'auth/profile.html', {
        'form': profile_form,
        'password_form': password_form,
        'reservation_history': reservation_history,
        'tournament_registrations': tournament_registrations,
        'match_history': match_history,
        'recent_activities': recent_activities,
        'total_reservations': total_reservations,
        'completed_reservations': completed_reservations,
        'pending_reservations': pending_reservations,
        'cancelled_reservations': cancelled_reservations,
        'confirmed_reservations': confirmed_reservations,
        'completed_matches': completed_matches,
        'tournament_count': tournament_count,
        'wins': wins,
        'favorite_courts': favorite_courts,
        'dashboard_url': urls['dashboard_url'],
        'profile_url': urls['profile_url'],
    })


def verify_otp_view(request):
    """
    OTP verification page for both registration and password reset.
    Displays 6-digit input fields with countdown timer and resend functionality.
    Accepts both regular form POST and AJAX requests.
    """
    if request.user.is_authenticated:
        return redirect('home')

    # Clean up any expired OTP records
    cleanup_expired_otps()

    email = request.session.get('otp_email')
    purpose = request.session.get('otp_purpose')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not email or not purpose:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'No verification in progress. Please start again.'}, status=400)
        messages.error(request, 'No verification in progress. Please start again.')
        if purpose == 'password_reset':
            return redirect('password_reset_request')
        return redirect('register')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        
        if not otp or len(otp) != 6 or not otp.isdigit():
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Please enter a valid 6-digit code.'}, status=400)
            messages.error(request, 'Please enter a valid 6-digit code.')
            return render(request, 'auth/otp_verification.html', {
                'email': email,
                'purpose': purpose,
                'expiry_minutes': OTP_EXPIRY_MINUTES,
            })
        
        success, otp_obj, error = verify_otp_code(email, otp, purpose)
        
        if success:
            if purpose == 'registration':
                # Activate the user account
                user_id = request.session.get('reg_user_id')
                try:
                    user = User.objects.get(id=user_id, email=email)
                    user.is_active = True
                    user.save(update_fields=['is_active'])
                    
                    # Create welcome notification
                    Notification.objects.create(
                        user=user,
                        message=f"Welcome to PickleSphere, {user.first_name}! Your account has been verified."
                    )
                    # Send welcome email
                    send_welcome_email(user)
                    
                    # Clear session
                    request.session.pop('otp_email', None)
                    request.session.pop('otp_purpose', None)
                    request.session.pop('reg_user_id', None)
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'redirect': reverse('login'),
                            'message': 'Email verified! Your account is now active. Please sign in.'
                        })
                    
                    messages.success(request, 'Email verified! Your account is now active. Please sign in.')
                    return redirect('login')
                except User.DoesNotExist:
                    if is_ajax:
                        return JsonResponse({'success': False, 'error': 'Account not found. Please register again.'}, status=400)
                    messages.error(request, 'Account not found. Please register again.')
                    return redirect('register')
            
            elif purpose == 'password_reset':
                # Mark OTP as verified in session, redirect to set new password
                request.session['otp_verified'] = True
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'redirect': reverse('password_reset_confirm'),
                        'message': 'Email verified! Please set a new password.'
                    })
                messages.success(request, 'Email verified! Please set a new password.')
                return redirect('password_reset_confirm')
        else:
            if is_ajax:
                remaining = otp_obj.attempts if otp_obj and hasattr(otp_obj, 'attempts') else ''
                return JsonResponse({'success': False, 'error': error or 'Invalid verification code.'}, status=400)
            messages.error(request, error or 'Invalid verification code.')
    
    # Non-AJAX GET requests render the standalone page
    return render(request, 'auth/otp_verification.html', {
        'email': email,
        'purpose': purpose,
        'expiry_minutes': OTP_EXPIRY_MINUTES,
    })


def resend_otp_view(request):
    """AJAX endpoint to resend OTP code with IP-based rate limiting."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    
    # IP-based rate limiting to prevent abuse
    ip_address = request.META.get('REMOTE_ADDR', 'unknown')
    cache_key = f'otp_resend_ip_{ip_address}'
    timeout = OTP_RESEND_WINDOW_MINUTES * 60
    
    # Atomically initialize or increment the counter
    if not cache.add(cache_key, 1, timeout=timeout):
        attempts = cache.incr(cache_key)
        if attempts > OTP_RESEND_MAX_PER_IP:
            return JsonResponse({
                'success': False,
                'error': f'Too many resend attempts. Please try again in {OTP_RESEND_WINDOW_MINUTES} minutes.'
            }, status=429)
    
    email = request.POST.get('email', '').strip()
    purpose = request.POST.get('purpose', '').strip()
    
    if not email or purpose not in ['registration', 'password_reset']:
        return JsonResponse({'success': False, 'error': 'Invalid request.'})
    
    user = None
    if purpose == 'password_reset':
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not found.'})
    elif purpose == 'registration':
        user_id = request.session.get('reg_user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
    
    ip = request.META.get('REMOTE_ADDR')
    success, otp_obj, error = create_and_send_otp(
        email=email,
        purpose=purpose,
        user=user,
        ip_address=ip,
    )
    
    if success:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': error or 'Failed to resend OTP.'})


@login_required
@admin_required
def user_list_view(request):
    """Super admin user list"""
    users = User.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    allowed_sort_fields = ['username', 'email', 'role', 'is_active', 'created_at', 'first_name', 'last_name']
    if sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        users = users.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/users/user_list.html', {
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'role_filter': role_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
    })


@login_required
@admin_required
def user_edit_view(request, user_id):
    
    user = get_object_or_404(User.objects.all(), id=user_id)
    
    if request.method == 'POST':
        form = AdminUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            was_active = user.is_active
            form.save()
            # Send reactivation email if user was reactivated
            if not was_active and user.is_active:
                send_account_reactivation_email(user)
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('super_admin_user_list')
    else:
        form = AdminUserUpdateForm(instance=user)
    
    return render(request, 'admin/users/user_form.html', {
        'form': form,
        'edit_user': user
    })


@login_required
@admin_required
def user_create_view(request):
    
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            created_user = form.save(commit=False)
            created_user.save()
            messages.success(request, f'User {created_user.username} created successfully!')
            return redirect('super_admin_user_list')
    else:
        form = AdminUserCreateForm()
    
    return render(request, 'admin/users/user_form.html', {'form': form})


@login_required
@admin_required
def user_delete_view(request, user_id):
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('super_admin_user_list')
    
    user_to_delete = get_object_or_404(User.objects.all(), id=user_id)
    if user_to_delete == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('super_admin_user_list')
    
    if not user_to_delete.is_active:
        messages.info(request, f'User {user_to_delete.username} is already inactive.')
        return redirect('super_admin_user_list')
    
    user_to_delete.is_active = False
    user_to_delete.save(update_fields=['is_active'])

    # Send account suspension notification
    send_account_suspension_email(user_to_delete, 'Account deactivated by admin')

    messages.success(request, f'User {user_to_delete.username} deactivated successfully.')
    return redirect('super_admin_user_list')


@login_required
@staff_or_admin_required
def user_activity_log(request):
    
    activities = UserActivity.objects.all().order_by('-created_at')[:100]
    return render(request, 'admin/activity_log.html', {'activities': activities})
