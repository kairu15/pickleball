"""User-facing dashboard, messages and ratings.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import user_required
from accounts.models import UserActivity
from dashboard.models import ContactMessage
from dashboard.models import Rating
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from notifications.models import Notification
from reservations.models import Reservation
from scoring.models import Match
from scoring.models import PlayerStats


@login_required
@user_required
def user_dashboard_view(request):
    """User dashboard"""
    today = timezone.now().date()
    
    # Upcoming reservations
    upcoming_reservations = Reservation.objects.filter(
        user=request.user,
        date__gte=today,
        status__in=['confirmed', 'pending']
    ).select_related('court', 'court__site').order_by('date', 'start_time')[:5]
    
    # Recent matches
    recent_matches = Match.objects.filter(
        Q(team1_player1=request.user) |
        Q(team1_player2=request.user) |
        Q(team2_player1=request.user) |
        Q(team2_player2=request.user)
    ).order_by('-created_at')[:5]
    
    # User stats
    try:
        stats = request.user.stats
    except PlayerStats.DoesNotExist:
        stats = None
    
    # Quick stats
    total_reservations = Reservation.objects.filter(user=request.user).exclude(status='cancelled').count()
    confirmed_reservations = Reservation.objects.filter(user=request.user, status='confirmed').count()
    pending_reservations = Reservation.objects.filter(user=request.user, status='pending').count()
    total_matches = Match.objects.filter(
        Q(team1_player1=request.user) |
        Q(team1_player2=request.user) |
        Q(team2_player1=request.user) |
        Q(team2_player2=request.user)
    ).count()
    
    # Recent activity
    recent_activities = UserActivity.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Unread notifications
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'user/dashboard.html', {
        'upcoming_reservations': upcoming_reservations,
        'recent_matches': recent_matches,
        'stats': stats,
        'total_reservations': total_reservations,
        'total_matches': total_matches,
        'confirmed_reservations': confirmed_reservations,
        'pending_reservations': pending_reservations,
        'recent_activities': recent_activities,
        'unread_notifications': unread_notifications,
        'unread_count': unread_count,
    })


@login_required
@user_required
def submit_rating_view(request, reservation_id):
    """User view for submitting a rating for a completed reservation"""
    
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Check if reservation is completed
    if reservation.status != 'completed':
        messages.error(request, 'You can only rate completed reservations.')
        return redirect('reservation_list')
    
    # Check if already rated
    if Rating.objects.filter(user=request.user, reservation=reservation).exists():
        messages.info(request, 'You have already rated this reservation.')
        return redirect('reservation_list')
    
    if request.method == 'POST':
        rating_value = request.POST.get('rating', 5)
        comment = request.POST.get('comment', '').strip()
        skip = request.POST.get('skip')
        
        if skip:
            # User chose to skip rating - mark as skipped (could store in session or a Skip model)
            messages.info(request, 'You can rate your experience later from your reservation details.')
            return redirect('reservation_list')
        
        try:
            rating_value = int(rating_value)
            if rating_value < 1 or rating_value > 5:
                raise ValueError
        except ValueError:
            messages.error(request, 'Please select a valid rating between 1 and 5 stars.')
            return redirect('submit_rating', reservation_id=reservation_id)
        
        # Create the rating
        Rating.objects.create(
            user=request.user,
            reservation=reservation,
            rating=rating_value,
            comment=comment if comment else None
        )
        
        messages.success(request, 'Thank you for your rating! Your feedback helps us improve.')
        return redirect('reservation_list')
    
    return render(request, 'user/submit_rating.html', {
        'reservation': reservation,
        'page_title': 'Rate Your Experience'
    })


@login_required
@user_required
def check_pending_rating_view(request):
    """AJAX view to check if user has any unrated completed reservations"""
    
    # Find completed reservations without ratings
    unrated_reservations = Reservation.objects.filter(
        user=request.user,
        status='completed'
    ).exclude(
        id__in=Rating.objects.filter(user=request.user).values_list('reservation_id', flat=True)
    ).select_related('court')
    
    if unrated_reservations.exists():
        reservation = unrated_reservations.first()
        return JsonResponse({
            'has_pending_rating': True,
            'reservation_id': reservation.id,
            'court_name': reservation.court.name,
            'date': reservation.date.strftime('%B %d, %Y')
        })
    
    return JsonResponse({'has_pending_rating': False})


@login_required
@user_required
def user_messages_view(request):
    """User view to display their contact messages and admin replies"""
    # Get messages sent by this user (matched by email)
    user_messages = ContactMessage.objects.filter(
        email=request.user.email
    ).order_by('-created_at')
    
    # Mark all unread replies as read when user views the page
    user_messages.filter(
        admin_reply__isnull=False,
        user_read_reply=False
    ).update(user_read_reply=True)
    
    # Count unread replies (before marking as read)
    unread_replies = user_messages.filter(
        admin_reply__isnull=False,
        user_read_reply=False
    ).count()
    
    return render(request, 'user/messages.html', {
        'messages': user_messages,
        'unread_replies': unread_replies,
    })
