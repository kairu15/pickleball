import csv
import json
from math import radians, sin, cos, sqrt, atan2

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, Avg, OuterRef, Subquery, FloatField
from django.db.models.functions import ExtractHour
from django.utils import timezone
from django.conf import settings
from notifications.email_utils import send_contact_form_email
from django.http import HttpResponse, JsonResponse
from datetime import datetime, timedelta

from accounts.models import User, UserActivity
from accounts.decorators import admin_required, staff_or_admin_required, user_required, super_admin_required
from courts.models import Court, Site, FavoriteCourt
from tournaments.models import Tournament

from reservations.models import Reservation
from payments.models import Payment
from scoring.models import Match, PlayerStats
from equipment.models import Equipment, EquipmentRental
from notifications.models import Notification
from .cache_utils import cache_anon_page, pages_cache_get_or_set, PAGES_CACHE_TIMEOUT
from .models import (
    AboutContent, AboutGalleryImage, Amenity, BusinessHour,
    ContactMessage, ContactInfo as CI, ContactContent, ContactFAQ,
    Facility, FAQPageContent, FAQCategory, FAQItem,
    GalleryImage, HomePageContent, Milestone,
    PricingContent, PricingTier, PricingFAQ,
    PrivacyContent, PrivacySection,
    Rating, SocialLink, SiteSettings,
    TeamMember, TermsContent, TermsSection,
    Testimonial, WhyChooseItem,
)

STATIC_CONTACT_PHONE = '09455470173'
STATIC_CONTACT_EMAIL = 'picklesphere@gmail.com'

# Helper to get contact info from DB or fallback to static defaults
def _get_contact_info():
    ci = CI.objects.first()
    if ci:
        return {
            'phone': ci.phone or STATIC_CONTACT_PHONE,
            'email': ci.email or STATIC_CONTACT_EMAIL,
            'address': ci.address or '123 Sports Avenue, Makati City',
            'city_country': ci.city_country or 'Metro Manila, Philippines',
            'google_maps_url': getattr(ci, 'google_maps_url', ''),
        }
    return None


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='home')
def home_view(request):
    """Public home page with personalized recommendations.
    Full-page cached for anonymous visitors; authenticated users always get a
    live, no-store render so their personalized recommendations stay accurate."""

    # Annotate average rating on courts
    rating_subquery = Rating.objects.filter(
        reservation__court=OuterRef('pk')
    ).values('reservation__court').annotate(
        avg=Avg('rating')
    ).values('avg')

    # Will be updated with nearest courts if user has saved location
    featured_courts = Court.objects.filter(is_active=True, site__is_active=True).annotate(
        rating_avg=Subquery(rating_subquery, output_field=FloatField())
    )[:6]
    total_courts = Court.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True).count()
    sites = Site.objects.filter(is_active=True)[:4]

    def get_homepage_content(section, default):
        content = HomePageContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    homepage_text = {
        'hero_title': get_homepage_content('hero_title', 'Welcome to PickleSphere'),
        'hero_subtitle': get_homepage_content('hero_subtitle', 'The all-in-one platform connecting pickleball players with courts, tournaments, and equipment rentals nationwide. Find, book, and play — all in one place.'),
        'about_title': get_homepage_content('about_title', 'Your Pickleball Journey Starts Here'),
        'about_text': get_homepage_content('about_text', 'PickleSphere is a comprehensive platform that connects pickleball enthusiasts with courts, equipment, and tournaments across the country. Whether you are a beginner looking to learn or a seasoned pro seeking competition, we make it easy to find, book, and play.'),
        'cta_title': get_homepage_content('cta_title', 'Ready to Play?'),
        'cta_text': get_homepage_content('cta_text', 'Join thousands of pickleball players. Find courts, join tournaments, and be part of the community!'),
    }

    # Get upcoming tournaments
    upcoming_tournaments = Tournament.objects.filter(
        tournament_start__gte=timezone.now().date(), 
        status__in=['registration_open', 'in_progress', 'draft']
    ).order_by('tournament_start')[:3]

    # Get ratings for display (prioritize featured ratings, then fill with recent)
    
    # Calculate average rating
    rating_stats = Rating.objects.aggregate(
        average_rating=Avg('rating'),
        total_ratings=Count('id')
    )
    average_rating = rating_stats['average_rating'] or 0
    total_ratings = rating_stats['total_ratings'] or 0
    
    # Get featured ratings only (admin-controlled homepage display)
    featured_ratings_list = list(Rating.objects.select_related('user').filter(is_featured=True).order_by('-created_at')[:6])
    
    # Prepare ratings for template from featured ratings only
    ratings = []
    for rating in featured_ratings_list:
        ratings.append({
            'name': rating.user.get_full_name() or rating.user.username,
            'rating': rating.rating,
            'comment': rating.comment,
            'created_at': rating.created_at,
            'is_featured': rating.is_featured,
            'avatar': None
        })
    
    # Fallback if no ratings exist
    if not ratings:
        ratings = [
            {
                'name': 'John Martinez',
                'rating': 5,
                'comment': 'PickleSphere has completely transformed my pickleball experience. The courts are top-notch and the booking system is so convenient!',
                'avatar': None
            },
            {
                'name': 'Sarah Chen',
                'rating': 5,
                'comment': 'I love the tournament features! The match tracking and leaderboard system makes every game exciting. Highly recommend!',
                'avatar': None
            },
            {
                'name': 'Mike Thompson',
                'rating': 5,
                'comment': 'As someone new to pickleball, the equipment rental and friendly community made it easy to get started. Great facility!',
                'avatar': None
            }
        ]
        average_rating = 5.0
        total_ratings = 3

    # Get dynamic gallery images from database (or use defaults if none exist)
    db_gallery = GalleryImage.objects.filter(is_active=True)[:6]
    if db_gallery.exists():
        gallery_images = db_gallery
    else:
        # Fallback default gallery images
        gallery_images = [
            {'url': 'https://images.unsplash.com/photo-1622163642998-1ea36b1ade5b?w=400', 'alt': 'Pickleball Court', 'title': 'Premium Court'},
            {'url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400', 'alt': 'Indoor Court', 'title': 'Indoor Court'},
            {'url': 'https://images.unsplash.com/photo-1599582380599-6fd8a689ab86?w=400', 'alt': 'Players', 'title': 'Active Play'},
            {'url': 'https://images.unsplash.com/photo-1576610616656-d3aa5d1f4534?w=400', 'alt': 'Equipment', 'title': 'Equipment'},
            {'url': 'https://images.unsplash.com/photo-1622163642998-1ea36b1ade5b?w=400', 'alt': 'Tournament', 'title': 'Tournament'},
            {'url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400', 'alt': 'Facility', 'title': 'Facility'},
        ]

    # Get dynamic amenities from database (or use defaults if none exist)
    db_amenities = Amenity.objects.filter(is_active=True)[:6]
    if db_amenities.exists():
        amenities = db_amenities
    else:
        # Fallback default amenities
        amenities = [
            {'icon': 'fa-wifi', 'title': 'Free WiFi', 'description': 'High-speed internet throughout'},
            {'icon': 'fa-car', 'title': 'Free Parking', 'description': 'Ample parking space available'},
            {'icon': 'fa-shower', 'title': 'Locker Rooms', 'description': 'Clean facilities with showers'},
            {'icon': 'fa-coffee', 'title': 'Café & Lounge', 'description': 'Refreshments and rest area'},
            {'icon': 'fa-tools', 'title': 'Pro Shop', 'description': 'Equipment sales and rentals'},
            {'icon': 'fa-medal', 'title': 'Training', 'description': 'Professional coaching available'},
        ]

    # Calculate stats for home page
    current_year = datetime.now().year
    years_experience = max(1, current_year - 2024 + 1)
    tournaments_count = Tournament.objects.filter(status='completed').count()
    
    # Apply SiteSettings overrides if set
    site_settings = SiteSettings.objects.first()
    if site_settings:
        if site_settings.override_stat_courts is not None:
            total_courts = site_settings.override_stat_courts
        if site_settings.override_stat_players is not None:
            total_users = site_settings.override_stat_players
        if site_settings.override_stat_tournaments is not None:
            tournaments_count = site_settings.override_stat_tournaments
        if site_settings.override_stat_years is not None:
            years_experience = site_settings.override_stat_years

    # =================================================================
    # PERSONALIZED RECOMMENDATIONS (for logged-in users only)
    # =================================================================
    recommended_courts = []
    nearest_courts = []
    user_favorite_ids = []

    if request.user.is_authenticated:
        user = request.user
        # Get user's favorite court IDs
        user_favorite_ids = list(FavoriteCourt.objects.filter(
            user=user
        ).values_list('court_id', flat=True))

        # Get all active courts
        all_courts = Court.objects.filter(
            is_active=True, site__is_active=True
        ).select_related('site').annotate(
            rating_avg=Subquery(rating_subquery, output_field=FloatField())
        )[:50]

        # Get user's reservation history for preference analysis
        user_reservations = Reservation.objects.filter(
            user=user
        ).select_related('court')[:20]

        # Extract preferred court types from history
        preferred_types = set()
        for r in user_reservations:
            preferred_types.add(r.court.court_type)

        # Score each court for recommendations
        court_scores = []
        for court in all_courts:
            score = 0
            # +1 for matching skill level recommendation (indoor/outdoor)
            if court.court_type in preferred_types:
                score += 3
            # +2 if user has favorited this court
            if court.id in user_favorite_ids:
                score += 5
            # +1 if it's the same type as the user's skill level preference
            if user.skill_level == 'beginner' and court.court_type == 'indoor':
                score += 1
            court_scores.append((court, score))

        # Sort by score (highest first) and take top 6 for recommendations
        court_scores.sort(key=lambda x: -x[1])
        recommended_courts = [c for c, s in court_scores[:6] if s > 0]

        # If no scored courts, fall back to popular courts
        if not recommended_courts:
            popular_ids = Reservation.objects.filter(
                status__in=['confirmed', 'completed']
            ).values('court_id').annotate(
                cnt=Count('id')
            ).order_by('-cnt').values_list('court_id', flat=True)[:6]
            recommended_courts_list = [c for c in all_courts if c.id in popular_ids][:6]
            if not recommended_courts_list:
                recommended_courts_list = list(all_courts[:6])
            recommended_courts = recommended_courts_list

        # Nearest courts (using saved user coordinates)
        # Also used to populate featured_courts with location-based results
        if user.latitude and user.longitude:
            user_lat = float(user.latitude)
            user_lng = float(user.longitude)
            courts_with_dist = []
            for court in all_courts:
                site = court.site
                if site and site.latitude and site.longitude:
                    site_lat = float(site.latitude)
                    site_lng = float(site.longitude)
                    # Haversine formula
                    dlon = radians(site_lng - user_lng)
                    dlat = radians(site_lat - user_lat)
                    a = sin(dlat/2)**2 + cos(radians(user_lat)) * cos(radians(site_lat)) * sin(dlon/2)**2
                    c_val = 2 * atan2(sqrt(a), sqrt(1-a))
                    distance_km = 6371 * c_val
                    courts_with_dist.append((court, round(distance_km, 1)))
            courts_with_dist.sort(key=lambda x: x[1])
            # Use nearest 6 courts as featured (replaces generic list for logged-in users with location)
            featured_courts = [c for c, d in courts_with_dist[:6]]
            # Use the next 4 nearest courts for the "Near Your Location" section to avoid duplication
            nearest_courts = [{'court': c, 'distance_km': d} for c, d in courts_with_dist[6:10]]

    return render(request, 'public/home.html', {
        'featured_courts': featured_courts,
        'total_courts': total_courts,
        'total_users': total_users,
        'sites': sites,
        'upcoming_tournaments': upcoming_tournaments,
        'ratings': ratings,
        'average_rating': round(average_rating, 1),
        'total_ratings': total_ratings,
        'gallery_images': gallery_images,
        'amenities': amenities,
        'years_experience': years_experience,
        'tournaments_count': tournaments_count,
        'homepage_text': homepage_text,
        'recommended_courts': recommended_courts,
        'nearest_courts': nearest_courts,
        'user_favorite_ids': user_favorite_ids,
    })


@login_required
def dashboard_view(request):
    """Redirect to appropriate dashboard based on user role"""
    if request.user.is_super_admin():
        return redirect('super_admin_analytics')
    elif request.user.is_staff_member():
        return redirect('staff_dashboard')
    else:
        return redirect('user_dashboard')


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
@staff_or_admin_required
def staff_dashboard_view(request):
    """Staff dashboard"""
    
    today = timezone.now().date()
    
    # Today's reservations (system-wide in centralized model)
    today_reservations_qs = Reservation.objects.filter(
        date=today,
        status__in=['confirmed', 'pending']
    ).select_related('user', 'court', 'court__site')
    staff_reservations_qs = Reservation.objects.filter(
        status='pending'
    )
    pending_payments_qs = Payment.objects.filter(status='pending')
    
    today_reservations = today_reservations_qs.order_by('start_time')
    pending_reservations = staff_reservations_qs.count()
    pending_payments = pending_payments_qs.count()
    
    # Active matches
    active_matches = Match.objects.filter(status='ongoing').count()
    
    # Equipment stats
    equipment_qs = Equipment.objects.filter(is_active=True)
    equipment_rental_qs = EquipmentRental.objects.filter(status__in=['reserved', 'rented'])
    
    equipment_stats = {
        'total': equipment_qs.count(),
        'low_stock': equipment_qs.filter(quantity_available__lte=2).count(),
        'active_rentals': equipment_rental_qs.count(),
    }
    
    # Recent activity
    recent_activities = UserActivity.objects.all().order_by('-created_at')[:10]
    
    return render(request, 'staff/dashboard.html', {
        'today_reservations': today_reservations,
        'pending_reservations': pending_reservations,
        'pending_payments': pending_payments,
        'active_matches': active_matches,
        'equipment_stats': equipment_stats,
        'recent_activities': recent_activities
    })


def all_courts_view(request):
    """All courts page - accessible to all users"""

    # Annotate average rating on courts queryset
    rating_subq = Rating.objects.filter(
        reservation__court=OuterRef('pk')
    ).values('reservation__court').annotate(
        avg=Avg('rating')
    ).values('avg')

    courts = Court.objects.filter(is_active=True).select_related('site').annotate(
        rating_avg=Subquery(rating_subq, output_field=FloatField())
    )
    sites = Site.objects.filter(is_active=True)

    site_id = request.GET.get('site', '')
    if site_id:
        courts = courts.filter(site_id=site_id)

    court_type = request.GET.get('type', '')
    if court_type:
        courts = courts.filter(court_type=court_type)

    date = request.GET.get('date', '')
    if date:
        try:
            selected_date = datetime.strptime(date, '%Y-%m-%d').date()
            reserved_court_ids = Reservation.objects.filter(
                date=selected_date,
                status__in=['confirmed', 'pending']
            ).values_list('court_id', flat=True)
            courts = courts.exclude(id__in=reserved_court_ids)
        except ValueError:
            pass

    return render(request, 'public/courts/all_courts.html', {
        'courts': courts,
        'sites': sites,
        'selected_site': site_id,
        'selected_type': court_type,
        'selected_date': date,
    })


def court_view_view(request, court_id):
    """Court detail page - accessible to all users"""

    court = get_object_or_404(Court, id=court_id, is_active=True)

    today = datetime.now().date()
    upcoming_reservations = Reservation.objects.filter(
        court=court,
        date__gte=today,
        status__in=['confirmed', 'pending']
    ).order_by('date', 'start_time')[:10]

    return render(request, 'public/courts/court_view.html', {
        'court': court,
        'upcoming_reservations': upcoming_reservations
    })


@login_required
@super_admin_required
def admin_dashboard_view(request):
    """Super Admin dashboard with full system-wide analytics"""
    
    today = timezone.now().date()
    now = timezone.now()
    
    # Key metrics
    metrics = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_courts': Court.objects.filter(is_active=True).count(),
        'total_reservations': Reservation.objects.exclude(status='cancelled').count(),
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
        'confirmed_reservations': Reservation.objects.filter(status='confirmed').count(),
    }
    
    # Revenue stats
    revenue_stats = {
        'total_revenue': Payment.objects.filter(status='paid').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'today_revenue': Payment.objects.filter(
            status='paid',
            created_at__date=today
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        'month_revenue': Payment.objects.filter(
            status='paid',
            created_at__month=today.month,
            created_at__year=today.year
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_amount': Payment.objects.filter(status='pending').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
    }
    
    # Recent data
    recent_reservations = Reservation.objects.select_related(
        'user', 'court', 'court__site'
    ).order_by('-created_at')[:10]
    recent_payments = Payment.objects.select_related(
        'reservation', 'reservation__court', 'reservation__court__site', 'reservation__user'
    ).order_by('-created_at')[:10]
    recent_users = User.objects.all().order_by('-created_at')[:10]
    
    # Court usage statistics
    court_usage = Reservation.objects.filter(
        status__in=['confirmed', 'completed']
    ).values('court__name').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # User registration by month (last 6 months)
    months = []
    user_counts = []
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=i*30)
        months.append(month_date.strftime('%b'))
        count = User.objects.filter(
            created_at__month=month_date.month,
            created_at__year=month_date.year
        ).count()
        user_counts.append(count)
    
    # ========== PEAK HOURS CHART ==========
    # Get hourly distribution of reservations (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    hourly_bookings = Reservation.objects.filter(
        created_at__date__gte=thirty_days_ago,
        status__in=['confirmed', 'completed', 'pending']
    ).annotate(
        hour=ExtractHour('start_time')
    ).values('hour').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('hour')
    
    peak_hours_labels = []
    peak_hours_counts = []
    peak_hours_revenue = []
    for h in range(8, 23):  # 8 AM to 10 PM
        peak_hours_labels.append(f"{h}:00")
        found = next((item for item in hourly_bookings if item['hour'] == h), None)
        peak_hours_counts.append(found['count'] if found else 0)
        peak_hours_revenue.append(float(found['revenue'] or 0) if found else 0)
    
    # ========== REVENUE TREND (last 14 days) ==========
    fourteen_days_ago = today - timedelta(days=13)
    daily_revenues = Payment.objects.filter(
        status='paid',
        created_at__date__gte=fourteen_days_ago
    ).extra(
        select={'day': 'DATE(created_at)'}
    ).values('day').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('day')
    
    # Build 14-day array with zeros for days with no transactions
    revenue_trend_labels = []
    revenue_trend_values = []
    booking_trend_values = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        revenue_trend_labels.append(day.strftime('%b %d'))
        found = next((item for item in daily_revenues if item['day'] == day), None)
        revenue_trend_values.append(float(found['total'] or 0) if found else 0)
        booking_trend_values.append(found['count'] if found else 0)
    
    # ========== EQUIPMENT UTILIZATION ==========
    total_equipment = Equipment.objects.filter(is_active=True).count()
    total_capacity = Equipment.objects.filter(is_active=True).aggregate(
        total=Sum('quantity_total')
    )['total'] or 0
    total_available = Equipment.objects.filter(is_active=True).aggregate(
        total=Sum('quantity_available')
    )['total'] or 0
    total_rented = EquipmentRental.objects.filter(
        status__in=['reserved', 'rented']
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Most rented equipment
    most_rented = EquipmentRental.objects.values(
        'equipment__name', 'equipment__type'
    ).annotate(
        total_rented=Sum('quantity'),
        total_revenue=Sum('rental_fee')
    ).order_by('-total_rented')[:5]
    
    # Active rentals today
    today_rentals = EquipmentRental.objects.filter(
        created_at__date=today
    ).count()
    
    equipment_utilization = {
        'total_items': total_equipment,
        'total_capacity': total_capacity,
        'total_available': total_available,
        'in_use': total_capacity - total_available,
        'utilization_rate': round((total_capacity - total_available) / total_capacity * 100, 1) if total_capacity > 0 else 0,
        'total_rented': total_rented,
        'today_rentals': today_rentals,
        'most_rented': most_rented,
        'labels': [item['equipment__name'] for item in most_rented],
        'counts': [item['total_rented'] for item in most_rented],
    }
    
    # ========== CUSTOMER RATINGS STATISTICS ==========
    
    rating_stats = Rating.objects.aggregate(
        average_rating=Avg('rating'),
        total_ratings=Count('id')
    )
    rating_data = {
        'average_rating': round(rating_stats['average_rating'] or 0, 1),
        'total_ratings': rating_stats['total_ratings'] or 0,
        'featured_ratings': Rating.objects.filter(is_featured=True).count(),
        'five_star_ratings': Rating.objects.filter(rating=5).count(),
    }
    
    # ========== REVENUE COMPARISON (this month vs last month) ==========
    this_month_revenue = Payment.objects.filter(
        status='paid',
        created_at__year=today.year,
        created_at__month=today.month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    last_month = today.month - 1 if today.month > 1 else 12
    last_month_year = today.year if today.month > 1 else today.year - 1
    last_month_revenue = Payment.objects.filter(
        status='paid',
        created_at__year=last_month_year,
        created_at__month=last_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    revenue_growth = round(
        ((this_month_revenue - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 0,
        1
    )
    
    return render(request, 'admin/dashboard.html', {
        'metrics': metrics,
        'revenue_stats': revenue_stats,
        'recent_reservations': recent_reservations,
        'recent_payments': recent_payments,
        'recent_users': recent_users,

        'court_usage': court_usage,
        'months': months,
        'user_counts': user_counts,
        # Peak hours
        'peak_hours_labels': peak_hours_labels,
        'peak_hours_counts': peak_hours_counts,
        'peak_hours_revenue': peak_hours_revenue,
        # Revenue trend
        'revenue_trend_labels': revenue_trend_labels,
        'revenue_trend_values': revenue_trend_values,
        'booking_trend_values': booking_trend_values,
        # Equipment utilization
        'equipment_utilization': equipment_utilization,
        # Revenue comparison
        'this_month_revenue': this_month_revenue,
        'last_month_revenue': last_month_revenue,
        'revenue_growth': revenue_growth,
        # Customer ratings
        'rating_data': rating_data,
    })


@login_required
@super_admin_required
def cache_monitor_view(request):
    """Super Admin Cache Monitor page: backend stats, invalidation events and
    slow DB queries captured by SlowQueryMiddleware."""
    from .cache_utils import get_cache_stats, get_invalidation_events, get_slow_queries

    context = {
        'cache_stats': get_cache_stats(),
        'invalidation_events': get_invalidation_events()[:50],
        'slow_queries': get_slow_queries()[:50],
        'cache_backend': getattr(settings, 'CACHE_BACKEND_SETTING', 'locmem'),
        'pages_timeout': PAGES_CACHE_TIMEOUT,
        'cms_timeout': getattr(settings, 'CMS_CACHE_TIMEOUT', 300),
        'monitor_enabled': getattr(settings, 'CACHE_MONITOR_ENABLED', False),
        'slow_query_threshold': getattr(settings, 'SLOW_QUERY_THRESHOLD_MS', 150),
        'page_title': 'Cache Monitor',
    }
    return render(request, 'admin/cache_monitor.html', context)


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='pricing')
def pricing_view(request):
    """Pricing page - accessible to all users (cached for anonymous visitors)"""

    courts = Court.objects.filter(is_active=True)

    # Get content from database with fallback defaults
    def get_content(section, default):
        content = PricingContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    content = {
        'hero_badge': get_content('hero_badge', 'Transparent Pricing'),
        'hero_title': get_content('hero_title', 'Simple, Fair Pricing'),
        'hero_subtitle': get_content('hero_subtitle', 'Choose the perfect plan for your pickleball journey. No hidden fees, no surprises.'),
        'court_rates_title': get_content('court_rates_title', 'Hourly Court Rates'),
        'court_rates_subtitle': get_content('court_rates_subtitle', 'Premium courts at competitive prices'),
        'membership_title': get_content('membership_title', 'Membership Plans'),
        'membership_subtitle': get_content('membership_subtitle', 'Save more with our exclusive membership options'),
        'comparison_title': get_content('comparison_title', 'Compare Plans'),
        'comparison_subtitle': get_content('comparison_subtitle', 'Find the perfect fit for your needs'),
        'services_title': get_content('services_title', 'Equipment & Services'),
        'services_subtitle': get_content('services_subtitle', 'Everything you need for the perfect game'),
        'faq_title': get_content('faq_title', 'Frequently Asked Questions'),
        'faq_subtitle': get_content('faq_subtitle', 'Got questions? We\'ve got answers'),
        'cta_title': get_content('cta_title', 'Ready to Start Playing?'),
        'cta_subtitle': get_content('cta_subtitle', 'Book a court today and experience the best pickleball facility in town.'),
    }

    # Calculate pricing tiers based on court types
    standard_courts = courts.filter(court_type='standard')
    premium_courts = courts.filter(court_type='premium')
    indoor_courts = courts.filter(court_type='indoor')

    pricing_data = {
        'standard_rate': 200 if standard_courts.exists() else 200,
        'premium_rate': 350 if premium_courts.exists() else 350,
        'indoor_rate': 300 if indoor_courts.exists() else 300,
    }

    # Get membership tiers from database or use defaults
    db_tiers = PricingTier.objects.filter(is_active=True).order_by('display_order', 'price')
    if db_tiers.exists():
        membership_tiers = []
        for tier in db_tiers:
            membership_tiers.append({
                'name': tier.name,
                'price': float(tier.price),
                'period': tier.period,
                'features': tier.features,
                'recommended': tier.is_recommended
            })
    else:
        # Fallback default membership tiers
        membership_tiers = [
            {
                'name': 'Basic',
                'price': 0,
                'features': ['Court booking access', 'Online reservations', 'Basic equipment rental', 'No priority booking', 'No member discounts'],
                'recommended': False
            },
            {
                'name': 'Pro Member',
                'price': 400,
                'period': 'month',
                'features': ['All Basic features', '10% off court rentals', 'Priority booking', 'Free paddle rental', 'Tournament discounts'],
                'recommended': True
            },
            {
                'name': 'Elite',
                'price': 350,
                'period': 'month',
                'features': ['All Pro features', '20% off court rentals', 'Unlimited bookings', 'Free equipment use', 'Coaching sessions'],
                'recommended': False
            }
        ]

    # Get FAQs from database or use defaults
    db_faqs = PricingFAQ.objects.filter(is_active=True).order_by('display_order', '-created_at')
    if db_faqs.exists():
        faqs = db_faqs[:4]  # Get first 4 active FAQs
    else:
        # Fallback default FAQs
        faqs = [
            {
                'question': 'Can I cancel my booking?',
                'answer': 'Yes, you can cancel up to 24 hours before your scheduled time for a full refund. Cancellations within 24 hours may be subject to a fee.'
            },
            {
                'question': 'Do memberships auto-renew?',
                'answer': 'Yes, monthly memberships auto-renew unless cancelled. You can cancel anytime from your account settings.'
            },
            {
                'question': 'Can I upgrade my membership?',
                'answer': 'Absolutely! You can upgrade your membership at any time. The price difference will be prorated for the remaining period.'
            },
            {
                'question': 'Are there any hidden fees?',
                'answer': 'No hidden fees! The prices shown are exactly what you\'ll pay. Equipment rental and other services are clearly priced.'
            },
        ]

    return render(request, 'public/pricing.html', {
        'pricing': pricing_data,
        'content': content,
        'membership_tiers': membership_tiers,
        'faqs': faqs,
        'courts': courts
    })


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='about')
def about_view(request):
    """About page - accessible to all users (cached for anonymous visitors)"""

    # Get content from database with fallback defaults
    def get_content(section, default):
        content = AboutContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    # Get contact info from database or use defaults
    contact_info = _get_contact_info()
    if not contact_info:
        contact_info = {
            'phone': STATIC_CONTACT_PHONE,
            'email': STATIC_CONTACT_EMAIL,
            'address': '123 Sports Avenue, Makati City',
            'city_country': 'Metro Manila, Philippines',
        }

    content = {
        'hero_badge': get_content('hero_badge', 'Our Story'),
        'hero_title': get_content('hero_title', 'Welcome to PickleSphere'),
        'hero_subtitle': get_content('hero_subtitle', 'The Philippines\' premier pickleball platform, connecting players with courts, tournaments, and equipment nationwide.'),
        'mission_title': get_content('mission_title', 'Our Mission'),
        'mission_text': get_content('mission_text', 'To grow the sport of pickleball by providing a centralized platform that connects players with organizations, simplifies court reservations, streamlines tournament management, and fosters a vibrant, inclusive pickleball community across the Philippines.'),
        'mission_features': get_content('mission_features', 'Connect players to courts,Simplify court reservations,Streamline tournaments,Build community').split(','),
        'vision_title': get_content('vision_title', 'Our Vision'),
        'vision_text': get_content('vision_text', 'To become the leading pickleball ecosystem in Southeast Asia, where every player can easily find a court, join a tournament, and be part of a thriving community.'),
        'vision_features': get_content('vision_features', 'Leading ecosystem,Accessible to all,Empower players,Grow the sport').split(','),
        'stats_courts': get_content('stats_courts', 'Courts on Platform'),
        'stats_members': get_content('stats_members', 'Active Players'),
        'stats_years': get_content('stats_years', 'Years in Operation'),
        'stats_tournaments': get_content('stats_tournaments', 'Tournaments Hosted'),
        'offers_badge': get_content('offers_badge', 'WHAT WE OFFER'),
        'offers_title': get_content('offers_title', 'Platform Features'),
        'offers_subtitle': get_content('offers_subtitle', 'Everything you need for the perfect pickleball experience'),
        'howitworks_badge': get_content('howitworks_badge', 'HOW IT WORKS'),
        'howitworks_title': get_content('howitworks_title', 'Getting Started is Easy'),
        'howitworks_subtitle': get_content('howitworks_subtitle', 'Follow these simple steps to start playing'),
        'players_badge': get_content('players_badge', 'FOR PLAYERS'),
        'players_title': get_content('players_title', 'Benefits for Players'),
        'players_subtitle': get_content('players_subtitle', 'Everything you need to enjoy pickleball to the fullest'),
        'orgs_badge': get_content('orgs_badge', 'FOR ADMINISTRATORS'),
        'orgs_title': get_content('orgs_title', 'Benefits for Administrators'),
        'orgs_subtitle': get_content('orgs_subtitle', 'Powerful tools to manage courts, reservations, and tournaments'),
        'why_badge': get_content('why_badge', 'WHY PICKLESPHERE'),
        'why_title': get_content('why_title', 'Why Choose Our Platform?'),
        'why_subtitle': get_content('why_subtitle', 'We provide the best pickleball platform experience'),
        'gallery_badge': get_content('gallery_badge', 'GALLERY'),
        'gallery_title': get_content('gallery_title', 'Pickleball in Action'),
        'gallery_subtitle': get_content('gallery_subtitle', 'See what is happening across our courts and events'),
        'cta_title': get_content('cta_title', 'Join the PickleSphere Community'),
        'cta_subtitle': get_content('cta_subtitle', 'Whether you are a player looking for a court or an administrator managing the platform, PickleSphere is for you.'),
    }

    # Get dynamic stats

    # Auto-calculate years operating from 2024
    current_year = datetime.now().year
    years_operating = max(1, current_year - 2024 + 1)  # +1 to include 2024

    # Count actual completed tournaments
    tournaments_hosted = Tournament.objects.filter(status='completed').count()

    stats = {
        'total_courts': Court.objects.filter(is_active=True).count(),
        'total_members': User.objects.filter(is_active=True).count(),
        'years_operating': years_operating,
        'tournaments_hosted': tournaments_hosted
    }

    # Get gallery images from database
    gallery_images = AboutGalleryImage.objects.filter(is_active=True).order_by('display_order')

    # Calculate years experience for template
    current_year = datetime.now().year
    years_experience = max(1, current_year - 2024 + 1)

    return render(request, 'public/about.html', {
        'content': content,
        'stats': stats,
        'years_experience': years_experience,
        'gallery_images': gallery_images,
        'contact_info': contact_info,
    })


def _get_contact_page_data():
    """Build the full contact page payload from the database.
    Cached under 'contact_page_data' and invalidated whenever any contact CMS
    model changes (see dashboard/cache_signals.py)."""

    # Get content from database with fallback defaults
    def get_content(section, default):
        content = ContactContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    content = {
        'hero_badge': get_content('hero_badge', "We're Here to Help"),
        'hero_title': get_content('hero_title', 'Get in Touch'),
        'hero_subtitle': get_content('hero_subtitle', "We'd love to hear from you. Reach out for any questions, inquiries, or just to say hello!"),
        'phone_label': get_content('phone_label', 'Phone'),
        'phone_hours': get_content('phone_hours', 'Mon-Sat, 9AM - 6PM'),
        'email_label': get_content('email_label', 'Email Us'),
        'email_response': get_content('email_response', 'We reply within 24 hours'),
        'visit_label': get_content('visit_label', 'Our Office'),
        'visit_city': get_content('visit_city', ''),
        'form_title': get_content('form_title', 'Send us a Message'),
        'form_name_label': get_content('form_name_label', 'Your Name'),
        'form_email_label': get_content('form_email_label', 'Email Address'),
        'form_subject_label': get_content('form_subject_label', 'Subject'),
        'form_message_label': get_content('form_message_label', 'Message'),
        'form_submit_text': get_content('form_submit_text', 'Send Message'),
        'hours_title': get_content('hours_title', 'Platform Support Hours'),
        'quick_links_title': get_content('quick_links_title', 'Quick Links'),
        'social_title': get_content('social_title', 'Follow Us'),
        'faq_badge': get_content('faq_badge', 'FAQ'),
        'faq_title': get_content('faq_title', 'Frequently Asked Questions'),
        'faq_subtitle': get_content('faq_subtitle', 'Quick answers to common questions'),
        'cta_title': get_content('cta_title', 'Ready to Start Playing?'),
        'cta_subtitle': get_content('cta_subtitle', 'Join thousands of players enjoying pickleball through our platform. Find courts, join tournaments, and connect with the community!'),
    }

    # Get contact info from database or create default
    contact_info_obj = CI.objects.first()
    if contact_info_obj:
        contact_info = {
            'phone': STATIC_CONTACT_PHONE,
            'email': STATIC_CONTACT_EMAIL,
            'address': contact_info_obj.address,
            'city_country': contact_info_obj.city_country,
            'google_maps_url': contact_info_obj.google_maps_url,
        }
    else:
        # Fallback default contact info
        contact_info = {
            'phone': STATIC_CONTACT_PHONE,
            'email': STATIC_CONTACT_EMAIL,
            'address': '123 Sports Avenue, Makati City',
            'city_country': 'Metro Manila, Philippines',
            'google_maps_url': 'https://maps.google.com/?q=14.5547,121.0244',
        }

    # Get business hours from database or use defaults
    db_hours = BusinessHour.objects.filter(is_active=True).order_by('display_order')
    if db_hours.exists():
        business_hours = db_hours
    else:
        # Fallback default business hours
        business_hours = [
            {'day_range': 'Monday - Friday', 'hours': '6:00 AM - 10:00 PM', 'icon_color': 'primary'},
            {'day_range': 'Saturday', 'hours': '6:00 AM - 10:00 PM', 'icon_color': 'success'},
            {'day_range': 'Sunday', 'hours': '7:00 AM - 9:00 PM', 'icon_color': 'warning'},
            {'day_range': 'Holidays', 'hours': '8:00 AM - 8:00 PM', 'icon_color': 'danger'},
        ]

    # Get FAQs from database or use defaults
    db_faqs = ContactFAQ.objects.filter(is_active=True).order_by('display_order')
    if db_faqs.exists():
        faqs = db_faqs
    else:
        # Fallback default FAQs
        faqs = [
            {'question': 'How do I book a court?', 'answer': 'You can easily book a court through our online booking system. Create an account, select your preferred date and time, and complete the payment.', 'icon_color': 'primary'},
            {'question': 'Can I rent equipment?', 'answer': 'Yes! We offer paddle and ball rentals at affordable rates. Members enjoy free equipment rental as part of their membership benefits.', 'icon_color': 'success'},
            {'question': 'Do you offer coaching?', 'answer': 'Absolutely! We have certified pickleball coaches available for private and group lessons. Contact us to schedule a session.', 'icon_color': 'warning'},
            {'question': 'How do I join tournaments?', 'answer': 'Tournament registration is done through our website. Navigate to the Tournaments page, select an event, and click Register to join.', 'icon_color': 'info'},
        ]

    # Get social links from database or use defaults
    db_socials = SocialLink.objects.filter(is_active=True).order_by('display_order')
    if db_socials.exists():
        social_links = db_socials
    else:
        # Fallback default social links (empty - no social links shown)
        social_links = []

    return {
        'content': content,
        'contact_info': contact_info,
        'business_hours': business_hours,
        'faqs': faqs,
        'social_links': social_links,
    }


def contact_view(request):
    """Contact page - accessible to all users.
    NOT full-page cached because it contains a CSRF-protected POST form;
    its expensive content queries are cached at the data level instead and
    invalidated automatically when any contact CMS model changes."""

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if name and email and subject and message:
            # Save to database
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )

            # Send email using centralized email service
            send_contact_form_email({
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
            })
            messages.success(request, "Thank you for your message! We will get back to you soon.")
            return redirect("contact")
        else:
            messages.error(request, 'Please fill in all fields.')

    data = pages_cache_get_or_set('contact_page_data', _get_contact_page_data)
    return render(request, 'public/contact.html', data or {
        'content': {},
        'contact_info': {},
        'business_hours': [],
        'faqs': [],
        'social_links': [],
    })


@login_required
@admin_required
def homepage_management(request):
    """Homepage content management page"""


    amenities = Amenity.objects.filter(is_active=True).order_by('display_order')
    gallery_images = GalleryImage.objects.filter(is_active=True).order_by('display_order')
    homepage_content = HomePageContent.objects.filter(is_active=True)

    context = {
        'amenities': amenities,
        'gallery_images': gallery_images,
        'homepage_content': homepage_content,
        'page_title': 'Homepage Management'
    }
    return render(request, 'admin/homepage/homepage_management.html', context)


@login_required
@admin_required
def homepage_edit_content(request, content_id=None):
    """Edit a single homepage text content item"""


    content_item = None
    if content_id:
        content_item = get_object_or_404(HomePageContent, id=content_id)

    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'

        if content_item:
            content_item.section = section
            content_item.content = content_text
            content_item.is_active = is_active
            content_item.save()
            messages.success(request, 'Homepage content updated successfully!')
        else:
            HomePageContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Homepage content created successfully!')

        return redirect('super_admin_homepage')

    context = {
        'content_item': content_item,
        'section_choices': HomePageContent.SECTION_CHOICES,
        'page_title': 'Edit Homepage Content' if content_item else 'New Homepage Content'
    }
    return render(request, 'admin/homepage/homepage_edit_content.html', context)


@login_required
@admin_required
def populate_homepage_content(request):
    """Create or reactivate the default homepage text content."""

    if request.method != 'POST':
        return redirect('super_admin_homepage')


    default_content = {
        'hero_title': 'Welcome to PickleSphere',
        'hero_subtitle': 'The all-in-one platform connecting pickleball players with courts, tournaments, and equipment rentals nationwide. Find, book, and play — all in one place.',
        'about_title': 'Your Pickleball Journey Starts Here',
        'about_text': 'PickleSphere is a comprehensive platform that connects pickleball enthusiasts with courts, equipment, and tournaments across the country. Whether you are a beginner looking to learn or a seasoned pro seeking competition, we make it easy to find, book, and play.',
        'cta_title': 'Ready to Play?',
        'cta_text': 'Join thousands of pickleball players. Find courts, join tournaments, and be part of the community!',
    }

    created_count = 0
    updated_count = 0
    for section, content in default_content.items():
        item, created = HomePageContent.objects.update_or_create(
            section=section,
            defaults={
                'content': content,
                'is_active': True,
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    if created_count:
        messages.success(request, f'Default homepage text content added ({created_count} new, {updated_count} refreshed).')
    else:
        messages.success(request, 'Homepage text content refreshed with default values.')

    return redirect('super_admin_homepage')


@login_required
@admin_required
def toggle_featured_rating(request, rating_id):
    """Toggle featured status of a rating for homepage display"""
    
    rating = get_object_or_404(Rating, id=rating_id)
    
    # Toggle featured status
    rating.is_featured = not rating.is_featured
    rating.save()
    
    if rating.is_featured:
        messages.success(request, f'Rating from {rating.user.username} is now featured on the homepage.')
    else:
        messages.success(request, f'Rating from {rating.user.username} has been removed from featured.')
    
    return redirect('super_admin_homepage')


@login_required
@admin_required
def homepage_edit_testimonial(request, testimonial_id=None):
    """Edit or create a testimonial"""
    
    
    testimonial = None
    if testimonial_id:
        testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role')
        rating = request.POST.get('rating', 5)
        text = request.POST.get('text')
        display_order = request.POST.get('display_order', 0)
        
        if testimonial:
            testimonial.name = name
            testimonial.role = role
            testimonial.rating = rating
            testimonial.text = text
            testimonial.display_order = display_order
            # If admin is editing, ensure it's approved
            if not testimonial.is_approved:
                testimonial.is_approved = True
            testimonial.save()
            messages.success(request, 'Testimonial updated successfully!')
        else:
            # Admin-created testimonials are auto-approved
            Testimonial.objects.create(
                name=name,
                role=role,
                rating=rating,
                text=text,
                display_order=display_order,
                is_active=True,
                is_approved=True  # Auto-approve admin-created testimonials
            )
            messages.success(request, 'Testimonial created and approved successfully!')
        
        return redirect('super_admin_homepage')
    
    context = {
        'testimonial': testimonial,
        'page_title': 'Edit Testimonial' if testimonial else 'New Testimonial'
    }
    return render(request, 'admin/homepage/homepage_edit_testimonial.html', context)


@login_required
@admin_required
def homepage_edit_amenity(request, amenity_id=None):
    """Edit or create an amenity"""
    
    
    amenity = None
    if amenity_id:
        amenity = get_object_or_404(Amenity, id=amenity_id)
    
    if request.method == 'POST':
        icon = request.POST.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        display_order = request.POST.get('display_order', 0)
        
        if amenity:
            amenity.icon = icon
            amenity.title = title
            amenity.description = description
            amenity.display_order = display_order
            amenity.save()
            messages.success(request, 'Amenity updated successfully!')
        else:
            Amenity.objects.create(
                icon=icon,
                title=title,
                description=description,
                display_order=display_order,
                is_active=True
            )
            messages.success(request, 'Amenity created successfully!')
        
        return redirect('super_admin_homepage')
    
    context = {
        'amenity': amenity,
        'page_title': 'Edit Amenity' if amenity else 'New Amenity'
    }
    return render(request, 'admin/homepage/homepage_edit_amenity.html', context)


@login_required
@admin_required
def homepage_edit_gallery(request, gallery_id=None):
    """Edit or create a gallery image"""
    
    
    gallery = None
    if gallery_id:
        gallery = get_object_or_404(GalleryImage, id=gallery_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        alt_text = request.POST.get('alt_text')
        display_order = request.POST.get('display_order', 0)
        
        if gallery:
            gallery.title = title
            gallery.alt_text = alt_text
            gallery.display_order = display_order
            if request.FILES.get('image'):
                gallery.image = request.FILES['image']
            gallery.save()
            messages.success(request, 'Gallery image updated successfully!')
        else:
            if request.FILES.get('image'):
                GalleryImage.objects.create(
                    image=request.FILES['image'],
                    title=title,
                    alt_text=alt_text,
                    display_order=display_order,
                    is_active=True
                )
                messages.success(request, 'Gallery image created successfully!')
            else:
                messages.error(request, 'Please upload an image.')
                context = {
                    'gallery': gallery,
                    'page_title': 'Edit Gallery Image' if gallery else 'New Gallery Image'
                }
                return render(request, 'admin/homepage/homepage_edit_gallery.html', context)
        
        return redirect('super_admin_homepage')
    
    context = {
        'gallery': gallery,
        'page_title': 'Edit Gallery Image' if gallery else 'New Gallery Image'
    }
    return render(request, 'admin/homepage/homepage_edit_gallery.html', context)


@login_required
@admin_required
def homepage_delete_testimonial(request, testimonial_id):
    """Delete a testimonial"""
    
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    testimonial.delete()
    messages.success(request, 'Testimonial deleted successfully!')
    return redirect('super_admin_homepage')


@login_required
@admin_required
def homepage_delete_amenity(request, amenity_id):
    """Delete an amenity"""
    
    amenity = get_object_or_404(Amenity, id=amenity_id)
    amenity.delete()
    messages.success(request, 'Amenity deleted successfully!')
    return redirect('super_admin_homepage')


@login_required
@admin_required
def homepage_delete_gallery(request, gallery_id):
    """Delete a gallery image"""
    
    gallery = get_object_or_404(GalleryImage, id=gallery_id)
    gallery.delete()
    messages.success(request, 'Gallery image deleted successfully!')
    return redirect('super_admin_homepage')


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='privacy')
def privacy_policy_view(request):
    """Privacy Policy page - accessible to all users (cached for anonymous visitors)"""
    
    def get_content(section, default):
        content = PrivacyContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default
    
    sections = PrivacySection.objects.filter(is_active=True).order_by('section_number')
    
    context = {
        'hero_badge': get_content('hero_badge', 'Legal'),
        'hero_title': get_content('hero_title', 'Privacy Policy'),
        'hero_subtitle': get_content('hero_subtitle', ''),
        'last_updated_text': get_content('last_updated_text', 'Last Updated:'),
        'contact_email': get_content('contact_email', 'privacy@picklesphere.com'),
        'contact_phone': get_content('contact_phone', '09455470173'),
        'contact_address': get_content('contact_address', '123 Sports Complex Ave, Metro City'),
        'sections': sections,
    }
    return render(request, 'public/privacy_policy.html', context)


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='terms')
def terms_of_service_view(request):
    """Terms of Service page - accessible to all users (cached for anonymous visitors)"""
    
    def get_content(section, default):
        content = TermsContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default
    
    sections = TermsSection.objects.filter(is_active=True).order_by('section_number')
    
    context = {
        'hero_badge': get_content('hero_badge', 'Legal'),
        'hero_title': get_content('hero_title', 'Terms of Service'),
        'hero_subtitle': get_content('hero_subtitle', ''),
        'last_updated_text': get_content('last_updated_text', 'Last Updated:'),
        'contact_email': get_content('contact_email', 'legal@picklesphere.com'),
        'contact_phone': get_content('contact_phone', '09455470173'),
        'contact_address': get_content('contact_address', '123 Sports Complex Ave, Metro City'),
        'sections': sections,
    }
    return render(request, 'public/terms_of_service.html', context)


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='faq')
def faq_view(request):
    """FAQ page - accessible to all users (cached for anonymous visitors)"""
    
    # Get CMS content sections with fallback defaults
    def get_content(section, default):
        content = FAQPageContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default
    
    cms_contents = {
        'hero_badge': get_content('hero_badge', 'Need Help?'),
        'hero_title': get_content('hero_title', 'Frequently Asked Questions'),
        'hero_subtitle': get_content('hero_subtitle', 'Find answers to common questions about PickleSphere, our platform, and services'),
        'search_placeholder': get_content('search_placeholder', 'Search for answers...'),
        'contact_title': get_content('contact_title', 'Still Need Help?'),
        'contact_text': get_content('contact_text', "Can't find what you're looking for? Our support team is here to help!"),
        'cta_button_text': get_content('cta_button_text', 'Contact Us'),
    }
    
    # Get categories and questions from database with fallback to defaults
    db_categories = FAQCategory.objects.prefetch_related('questions').filter(is_active=True).order_by('display_order')
    
    if db_categories.exists():
        faq_categories = []
        for cat in db_categories:
            questions = cat.questions.filter(is_active=True).order_by('display_order')
            if questions.exists():
                faq_categories.append({
                    'name': cat.name,
                    'icon': cat.icon,
                    'questions': [
                        {'question': q.question, 'answer': q.answer}
                        for q in questions
                    ]
                })
    
    if not db_categories.exists() or not faq_categories:
        # Fallback default FAQ categories
        faq_categories = [
            {
                'name': 'Reservations & Bookings',
                'icon': 'fa-calendar-check',
                'questions': [
                    {'question': 'How do I book a court?', 'answer': 'You can book a court by navigating to the "Find Courts" page, selecting your preferred court, date, and time slot.'},
                    {'question': 'Can I cancel or reschedule my reservation?', 'answer': 'Yes, you can cancel or reschedule your reservation up to 24 hours before your scheduled time.'},
                ]
            },
            {
                'name': 'Payments & Pricing',
                'icon': 'fa-money-bill-wave',
                'questions': [
                    {'question': 'What payment methods do you accept?', 'answer': 'We accept various payment methods including credit/debit cards, GCash, PayMaya, and bank transfers.'},
                    {'question': 'How do I get a refund?', 'answer': 'Refund requests can be submitted through the "Payment History" page. Refunds are processed within 5-7 business days.'},
                ]
            },
            {
                'name': 'Account & Technical',
                'icon': 'fa-user-circle',
                'questions': [
                    {'question': 'How do I reset my password?', 'answer': 'Click "Forgot Password" on the login page and enter your email address.'},
                    {'question': 'How do I contact customer support?', 'answer': f'You can reach us through the Contact page, email us at {STATIC_CONTACT_EMAIL}, or call us at {STATIC_CONTACT_PHONE}.'},
                ]
            },
        ]
    
    return render(request, 'public/faq.html', {
        'faq_categories': faq_categories,
        'cms_contents': cms_contents,
    })


# ============================================================================
# PRICING PAGE MANAGEMENT
# ============================================================================

@login_required
@admin_required
def pricing_management(request):
    """Pricing page content management"""
    
    
    content = PricingContent.objects.filter(is_active=True).order_by('section')
    tiers = PricingTier.objects.all().order_by('display_order', 'price')
    faqs = PricingFAQ.objects.all().order_by('display_order')
    
    context = {
        'content': content,
        'tiers': tiers,
        'faqs': faqs,
        'page_title': 'Pricing Page Management'
    }
    return render(request, 'admin/pricing/pricing_management.html', context)


@login_required
@admin_required
def pricing_edit_content(request, content_id=None):
    """Edit or create pricing page content"""
    
    
    content_item = None
    if content_id:
        content_item = get_object_or_404(PricingContent, id=content_id)
    
    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'
        
        if content_item:
            content_item.section = section
            content_item.content = content_text
            content_item.is_active = is_active
            content_item.save()
            messages.success(request, 'Content updated successfully!')
        else:
            PricingContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Content created successfully!')
        
        return redirect('super_admin_pricing')
    
    context = {
        'content_item': content_item,
        'section_choices': PricingContent.SECTION_CHOICES,
        'page_title': 'Edit Pricing Content' if content_item else 'New Pricing Content'
    }
    return render(request, 'admin/pricing/pricing_edit_content.html', context)


@login_required
@admin_required
def pricing_delete_content(request, content_id):
    """Delete pricing content"""
    
    content = get_object_or_404(PricingContent, id=content_id)
    content.delete()
    messages.success(request, 'Content deleted successfully!')
    return redirect('super_admin_pricing')


@login_required
@admin_required
def pricing_edit_tier(request, tier_id=None):
    """Edit or create pricing tier"""
    
    
    tier = None
    if tier_id:
        tier = get_object_or_404(PricingTier, id=tier_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price', 0)
        period = request.POST.get('period', '')
        description = request.POST.get('description', '')
        features_json = request.POST.get('features', '[]')
        is_recommended = request.POST.get('is_recommended') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        try:
            features = json.loads(features_json)
        except json.JSONDecodeError:
            features = []
        
        if tier:
            tier.name = name
            tier.price = price
            tier.period = period
            tier.description = description
            tier.features = features
            tier.is_recommended = is_recommended
            tier.is_active = is_active
            tier.display_order = display_order
            tier.save()
            messages.success(request, 'Pricing tier updated successfully!')
        else:
            PricingTier.objects.create(
                name=name,
                price=price,
                period=period,
                description=description,
                features=features,
                is_recommended=is_recommended,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Pricing tier created successfully!')
        
        return redirect('super_admin_pricing')
    
    context = {
        'tier': tier,
        'page_title': 'Edit Pricing Tier' if tier else 'New Pricing Tier'
    }
    return render(request, 'admin/pricing/pricing_edit_tier.html', context)


@login_required
@admin_required
def pricing_delete_tier(request, tier_id):
    """Delete pricing tier"""
    
    tier = get_object_or_404(PricingTier, id=tier_id)
    tier.delete()
    messages.success(request, 'Pricing tier deleted successfully!')
    return redirect('super_admin_pricing')


@login_required
@admin_required
def pricing_edit_faq(request, faq_id=None):
    """Edit or create pricing FAQ"""
    
    
    faq = None
    if faq_id:
        faq = get_object_or_404(PricingFAQ, id=faq_id)
    
    if request.method == 'POST':
        question = request.POST.get('question')
        answer = request.POST.get('answer')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if faq:
            faq.question = question
            faq.answer = answer
            faq.is_active = is_active
            faq.display_order = display_order
            faq.save()
            messages.success(request, 'FAQ updated successfully!')
        else:
            PricingFAQ.objects.create(
                question=question,
                answer=answer,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'FAQ created successfully!')
        
        return redirect('super_admin_pricing')
    
    context = {
        'faq': faq,
        'page_title': 'Edit Pricing FAQ' if faq else 'New Pricing FAQ'
    }
    return render(request, 'admin/pricing/pricing_edit_faq.html', context)


@login_required
@admin_required
def pricing_delete_faq(request, faq_id):
    """Delete pricing FAQ"""
    
    faq = get_object_or_404(PricingFAQ, id=faq_id)
    faq.delete()
    messages.success(request, 'FAQ deleted successfully!')
    return redirect('super_admin_pricing')


# ============================================================================
# ABOUT PAGE MANAGEMENT
# ============================================================================

@login_required
@admin_required
def about_management(request):
    """About page content management"""


    content = AboutContent.objects.filter(is_active=True).order_by('section')
    milestones = Milestone.objects.all().order_by('display_order', 'year')
    team_members = TeamMember.objects.all().order_by('display_order')
    facilities = Facility.objects.all().order_by('display_order')
    why_items = WhyChooseItem.objects.all().order_by('display_order')
    gallery_images = AboutGalleryImage.objects.filter(is_active=True).order_by('display_order')

    context = {
        'content': content,
        'milestones': milestones,
        'team_members': team_members,
        'facilities': facilities,
        'why_items': why_items,
        'gallery_images': gallery_images,
        'page_title': 'About Page Management'
    }
    return render(request, 'admin/about/about_management.html', context)


@login_required
@admin_required
def about_edit_content(request, content_id=None):
    """Edit or create about page content"""
    
    
    content_item = None
    if content_id:
        content_item = get_object_or_404(AboutContent, id=content_id)
    
    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'
        
        if content_item:
            content_item.section = section
            content_item.content = content_text
            content_item.is_active = is_active
            content_item.save()
            messages.success(request, 'Content updated successfully!')
        else:
            AboutContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Content created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'content_item': content_item,
        'section_choices': AboutContent.SECTION_CHOICES,
        'page_title': 'Edit About Content' if content_item else 'New About Content'
    }
    return render(request, 'admin/about/about_edit_content.html', context)


@login_required
@admin_required
def about_delete_content(request, content_id):
    """Delete about content"""
    
    content = get_object_or_404(AboutContent, id=content_id)
    content.delete()
    messages.success(request, 'Content deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_milestone(request, milestone_id=None):
    """Edit or create milestone"""
    
    
    milestone = None
    if milestone_id:
        milestone = get_object_or_404(Milestone, id=milestone_id)
    
    if request.method == 'POST':
        year = request.POST.get('year')
        title = request.POST.get('title')
        description = request.POST.get('description')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if milestone:
            milestone.year = year
            milestone.title = title
            milestone.description = description
            milestone.color = color
            milestone.is_active = is_active
            milestone.display_order = display_order
            milestone.save()
            messages.success(request, 'Milestone updated successfully!')
        else:
            Milestone.objects.create(
                year=year,
                title=title,
                description=description,
                color=color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Milestone created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'milestone': milestone,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Milestone' if milestone else 'New Milestone'
    }
    return render(request, 'admin/about/about_edit_milestone.html', context)


@login_required
@admin_required
def about_delete_milestone(request, milestone_id):
    """Delete milestone"""
    
    milestone = get_object_or_404(Milestone, id=milestone_id)
    milestone.delete()
    messages.success(request, 'Milestone deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_team_member(request, member_id=None):
    """Edit or create team member"""
    
    
    member = None
    if member_id:
        member = get_object_or_404(TeamMember, id=member_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role')
        bio = request.POST.get('bio')
        linkedin_url = request.POST.get('linkedin_url', '')
        twitter_url = request.POST.get('twitter_url', '')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if member:
            member.name = name
            member.role = role
            member.bio = bio
            member.linkedin_url = linkedin_url
            member.twitter_url = twitter_url
            member.color = color
            member.is_active = is_active
            member.display_order = display_order
            if request.FILES.get('photo'):
                member.photo = request.FILES['photo']
            member.save()
            messages.success(request, 'Team member updated successfully!')
        else:
            TeamMember.objects.create(
                name=name,
                role=role,
                bio=bio,
                linkedin_url=linkedin_url,
                twitter_url=twitter_url,
                color=color,
                is_active=is_active,
                display_order=display_order,
                photo=request.FILES.get('photo')
            )
            messages.success(request, 'Team member created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'member': member,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Team Member' if member else 'New Team Member'
    }
    return render(request, 'admin/about/about_edit_team_member.html', context)


@login_required
@admin_required
def about_delete_team_member(request, member_id):
    """Delete team member"""
    
    member = get_object_or_404(TeamMember, id=member_id)
    member.delete()
    messages.success(request, 'Team member deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_facility(request, facility_id=None):
    """Edit or create facility"""
    
    
    facility = None
    if facility_id:
        facility = get_object_or_404(Facility, id=facility_id)
    
    if request.method == 'POST':
        icon = request.POST.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if facility:
            facility.icon = icon
            facility.title = title
            facility.description = description
            facility.color = color
            facility.is_active = is_active
            facility.display_order = display_order
            facility.save()
            messages.success(request, 'Facility updated successfully!')
        else:
            Facility.objects.create(
                icon=icon,
                title=title,
                description=description,
                color=color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Facility created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'facility': facility,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger'), ('purple', 'Purple')],
        'page_title': 'Edit Facility' if facility else 'New Facility'
    }
    return render(request, 'admin/about/about_edit_facility.html', context)


@login_required
@admin_required
def about_delete_facility(request, facility_id):
    """Delete facility"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    facility.delete()
    messages.success(request, 'Facility deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_why_item(request, item_id=None):
    """Edit or create why choose item"""
    
    
    item = None
    if item_id:
        item = get_object_or_404(WhyChooseItem, id=item_id)
    
    if request.method == 'POST':
        icon = request.POST.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if item:
            item.icon = icon
            item.title = title
            item.description = description
            item.color = color
            item.is_active = is_active
            item.display_order = display_order
            item.save()
            messages.success(request, 'Item updated successfully!')
        else:
            WhyChooseItem.objects.create(
                icon=icon,
                title=title,
                description=description,
                color=color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Item created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'item': item,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Why Choose Item' if item else 'New Why Choose Item'
    }
    return render(request, 'admin/about/about_edit_why_item.html', context)


@login_required
@admin_required
def about_delete_why_item(request, item_id):
    """Delete why choose item"""
    
    item = get_object_or_404(WhyChooseItem, id=item_id)
    item.delete()
    messages.success(request, 'Item deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_add_gallery_image(request):
    """Add gallery image for about page"""
    
    
    if request.method == 'POST':
        image = request.FILES.get('image')
        title = request.POST.get('title', '')
        alt_text = request.POST.get('alt_text', '')
        display_order = request.POST.get('display_order', 0)
        
        if image:
            AboutGalleryImage.objects.create(
                image=image,
                title=title,
                alt_text=alt_text,
                display_order=display_order
            )
            messages.success(request, 'Gallery image uploaded successfully!')
        else:
            messages.error(request, 'Please select an image to upload.')
        
        return redirect('super_admin_about')
    
    return redirect('super_admin_about')


@login_required
@admin_required
def about_delete_gallery_image(request, image_id):
    """Delete gallery image"""
    
    image = get_object_or_404(AboutGalleryImage, id=image_id)
    image.delete()
    messages.success(request, 'Gallery image deleted successfully!')
    return redirect('super_admin_about')


# ============================================================================
# CONTACT PAGE MANAGEMENT
# ============================================================================

@login_required
@admin_required
def contact_management(request):
    """Contact page content management"""
    
    
    content = ContactContent.objects.filter(is_active=True).order_by('section')
    contact_info = CI.objects.first()
    business_hours = BusinessHour.objects.all().order_by('display_order')
    faqs = ContactFAQ.objects.all().order_by('display_order')
    social_links = SocialLink.objects.all().order_by('display_order')
    
    context = {
        'content': content,
        'contact_info': contact_info,
        'business_hours': business_hours,
        'faqs': faqs,
        'social_links': social_links,
        'page_title': 'Contact Page Management'
    }
    return render(request, 'admin/contact/contact_management.html', context)


@login_required
@admin_required
def contact_edit_content(request, content_id=None):
    """Edit or create contact page content"""
    
    
    content_item = None
    if content_id:
        content_item = get_object_or_404(ContactContent, id=content_id)
    
    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'
        
        if content_item:
            content_item.section = section
            content_item.content = content_text
            content_item.is_active = is_active
            content_item.save()
            messages.success(request, 'Content updated successfully!')
        else:
            ContactContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Content created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'content_item': content_item,
        'section_choices': ContactContent.SECTION_CHOICES,
        'page_title': 'Edit Contact Content' if content_item else 'New Contact Content'
    }
    return render(request, 'admin/contact/contact_edit_content.html', context)


@login_required
@admin_required
def contact_delete_content(request, content_id):
    """Delete contact content"""
    
    content = get_object_or_404(ContactContent, id=content_id)
    content.delete()
    messages.success(request, 'Content deleted successfully!')
    return redirect('super_admin_contact')


@login_required
@admin_required
def contact_edit_info(request):
    """Edit contact information"""
    
    
    contact_info = CI.objects.first()
    
    if request.method == 'POST':
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        city_country = request.POST.get('city_country')
        google_maps_url = request.POST.get('google_maps_url', '')
        
        if contact_info:
            contact_info.phone = phone
            contact_info.email = email
            contact_info.address = address
            contact_info.city_country = city_country
            contact_info.google_maps_url = google_maps_url
            contact_info.save()
            messages.success(request, 'Contact information updated successfully!')
        else:
            CI.objects.create(
                phone=phone,
                email=email,
                address=address,
                city_country=city_country,
                google_maps_url=google_maps_url
            )
            messages.success(request, 'Contact information created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'contact_info': contact_info,
        'page_title': 'Edit Contact Information'
    }
    return render(request, 'admin/contact/contact_edit_info.html', context)


@login_required
@admin_required
def contact_edit_business_hour(request, hour_id=None):
    """Edit or create business hour"""
    
    
    hour = None
    if hour_id:
        hour = get_object_or_404(BusinessHour, id=hour_id)
    
    if request.method == 'POST':
        day_range = request.POST.get('day_range')
        hours = request.POST.get('hours')
        icon_color = request.POST.get('icon_color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if hour:
            hour.day_range = day_range
            hour.hours = hours
            hour.icon_color = icon_color
            hour.is_active = is_active
            hour.display_order = display_order
            hour.save()
            messages.success(request, 'Business hour updated successfully!')
        else:
            BusinessHour.objects.create(
                day_range=day_range,
                hours=hours,
                icon_color=icon_color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Business hour created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'hour': hour,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Business Hour' if hour else 'New Business Hour'
    }
    return render(request, 'admin/contact/contact_edit_business_hour.html', context)


@login_required
@admin_required
def contact_delete_business_hour(request, hour_id):
    """Delete business hour"""
    
    hour = get_object_or_404(BusinessHour, id=hour_id)
    hour.delete()
    messages.success(request, 'Business hour deleted successfully!')
    return redirect('super_admin_contact')


@login_required
@admin_required
def contact_edit_faq(request, faq_id=None):
    """Edit or create contact FAQ"""
    
    
    faq = None
    if faq_id:
        faq = get_object_or_404(ContactFAQ, id=faq_id)
    
    if request.method == 'POST':
        question = request.POST.get('question')
        answer = request.POST.get('answer')
        icon_color = request.POST.get('icon_color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if faq:
            faq.question = question
            faq.answer = answer
            faq.icon_color = icon_color
            faq.is_active = is_active
            faq.display_order = display_order
            faq.save()
            messages.success(request, 'FAQ updated successfully!')
        else:
            ContactFAQ.objects.create(
                question=question,
                answer=answer,
                icon_color=icon_color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'FAQ created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'faq': faq,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Contact FAQ' if faq else 'New Contact FAQ'
    }
    return render(request, 'admin/contact/contact_edit_faq.html', context)


@login_required
@admin_required
def contact_delete_faq(request, faq_id):
    """Delete contact FAQ"""
    
    faq = get_object_or_404(ContactFAQ, id=faq_id)
    faq.delete()
    messages.success(request, 'FAQ deleted successfully!')
    return redirect('super_admin_contact')


@login_required
@admin_required
def contact_edit_social_link(request, link_id=None):
    """Edit or create social link"""
    
    
    link = None
    if link_id:
        link = get_object_or_404(SocialLink, id=link_id)
    
    if request.method == 'POST':
        platform = request.POST.get('platform')
        url = request.POST.get('url')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if link:
            link.platform = platform
            link.url = url
            link.is_active = is_active
            link.display_order = display_order
            link.save()
            messages.success(request, 'Social link updated successfully!')
        else:
            SocialLink.objects.create(
                platform=platform,
                url=url,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Social link created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'link': link,
        'platform_choices': SocialLink._meta.get_field('platform').choices,
        'page_title': 'Edit Social Link' if link else 'New Social Link'
    }
    return render(request, 'admin/contact/contact_edit_social_link.html', context)


@login_required
@admin_required
def contact_delete_social_link(request, link_id):
    """Delete social link"""
    
    link = get_object_or_404(SocialLink, id=link_id)
    link.delete()
    messages.success(request, 'Social link deleted successfully!')
    return redirect('super_admin_contact')


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


# Deprecated testimonial views - replaced by rating system
# Kept for reference but no longer used in URLs
@login_required
@admin_required
def contact_messages_view(request):
    """Admin view to display all contact messages"""
    
    messages_list = ContactMessage.objects.all().order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        messages_list = messages_list.filter(status=status_filter)
    
    # Count unread messages
    unread_count = ContactMessage.objects.filter(is_read=False).count()
    
    return render(request, 'admin/contact/contact_messages.html', {
        'messages': messages_list,
        'unread_count': unread_count,
        'status_filter': status_filter,
    })


@login_required
@admin_required
def contact_message_detail_view(request, message_id):
    """Admin view to view and reply to a specific contact message"""
    
    message = get_object_or_404(ContactMessage, id=message_id)
    
    # Mark as read when viewed
    if not message.is_read:
        message.is_read = True
        message.status = 'read'
        message.save()
    
    if request.method == 'POST':
        reply_text = request.POST.get('reply')
        action = request.POST.get('action')
        
        if action == 'reply' and reply_text:
            # Save the reply
            message.admin_reply = reply_text
            message.replied_by = request.user
            message.replied_at = timezone.now()
            message.status = 'replied'
            message.save()
            
            # Find the user by email and create a notification
            try:
                user = User.objects.get(email=message.email)
                Notification.objects.create(
                    user=user,
                    message=f"Admin replied to your message: {message.get_subject_display()}",
                    notification_type='success'
                )
            except User.DoesNotExist:
                # User doesn't exist, skip notification
                pass
            
            # Send email to the sender
            try:
                send_mail(
                    f'Re: {message.get_subject_display()} - PickleSphere',
                    f'Hi {message.name},\n\nThank you for contacting us. Here is our reply:\n\n{reply_text}\n\nBest regards,\nPickleSphere Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [message.email],
                    fail_silently=True
                )
                messages.success(request, 'Reply sent successfully!')
            except Exception:
                messages.success(request, 'Reply saved successfully!')
            
            return redirect('super_admin_contact_messages')
        
        elif action == 'close':
            message.status = 'closed'
            message.save()
            messages.success(request, 'Message closed.')
            return redirect('super_admin_contact_messages')
    
    return render(request, 'admin/contact/contact_message_detail.html', {
        'message': message,
    })


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



@login_required
def admin_reject_testimonial_view(request, testimonial_id):
    """DEPRECATED: Testimonials replaced by rating system"""
    messages.info(request, 'Testimonials have been replaced by our new rating system.')
    return redirect('super_admin_homepage')


@login_required
@admin_required
def dashboard_export_view(request):
    """Export dashboard analytics data as CSV"""

    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dashboard_report_{today.isoformat()}.csv"'

    writer = csv.writer(response)

    # Header
    writer.writerow(['PickleSphere Dashboard Report'])
    writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])

    # Key Metrics
    writer.writerow(['KEY METRICS'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Users', User.objects.count()])
    writer.writerow(['Active Users', User.objects.filter(is_active=True).count()])
    writer.writerow(['Total Courts', Court.objects.filter(is_active=True).count()])
    writer.writerow(['Total Reservations', Reservation.objects.exclude(status='cancelled').count()])
    writer.writerow(['Today Reservations', Reservation.objects.filter(date=today).count()])
    writer.writerow(['Pending Reservations', Reservation.objects.filter(status='pending').count()])
    writer.writerow([])

    # Revenue
    writer.writerow(['REVENUE'])
    writer.writerow(['Metric', 'Value'])
    total_rev = Payment.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    today_rev = Payment.objects.filter(status='paid', created_at__date=today).aggregate(Sum('amount'))['amount__sum'] or 0
    writer.writerow(['Total Revenue', f'₱{total_rev:.2f}'])
    writer.writerow(['Today Revenue', f'₱{today_rev:.2f}'])
    writer.writerow([])

    # Court Usage
    writer.writerow(['COURT USAGE (Top 10)'])
    writer.writerow(['Court', 'Reservations'])
    court_usage_data = Reservation.objects.filter(
        status__in=['confirmed', 'completed']
    ).values('court__name').annotate(total=Count('id')).order_by('-total')[:10]
    for item in court_usage_data:
        writer.writerow([item['court__name'], item['total']])
    writer.writerow([])

    # Equipment
    writer.writerow(['EQUIPMENT UTILIZATION'])
    writer.writerow(['Metric', 'Value'])
    total_cap = Equipment.objects.filter(is_active=True).aggregate(total=Sum('quantity_total'))['total'] or 0
    total_avail = Equipment.objects.filter(is_active=True).aggregate(total=Sum('quantity_available'))['total'] or 0
    writer.writerow(['Total Capacity', total_cap])
    writer.writerow(['Currently Available', total_avail])
    writer.writerow(['Currently In Use', total_cap - total_avail])
    writer.writerow([])

    # Recent Reservations
    writer.writerow(['RECENT RESERVATIONS (Last 10)'])
    writer.writerow(['ID', 'User', 'Court', 'Date', 'Status'])
    for res in Reservation.objects.all().order_by('-created_at')[:10]:
        writer.writerow([res.id, res.user.username, res.court.name, res.date, res.status])

    return response


@login_required
@admin_required
def rating_list_view(request):
    """Admin view to display all customer ratings with overview statistics"""


    # Get all ratings with related user and reservation
    ratings = Rating.objects.select_related('user', 'reservation', 'reservation__court').order_by('-created_at')

    # Calculate statistics
    rating_stats = Rating.objects.aggregate(
        average_rating=Avg('rating'),
        total_ratings=Count('id')
    )
    total_ratings = rating_stats['total_ratings'] or 0

    # Get rating distribution
    distribution = Rating.objects.values('rating').annotate(count=Count('id')).order_by('-rating')
    rating_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for item in distribution:
        rating_distribution[item['rating']] = item['count']

    # Calculate distribution percentages for template
    distribution_list = []
    for stars in [5, 4, 3, 2, 1]:
        count = rating_distribution.get(stars, 0)
        percentage = int((count / total_ratings * 100)) if total_ratings > 0 else 0
        distribution_list.append({
            'stars': stars,
            'count': count,
            'percentage': percentage,
        })

    # Filter by rating if provided
    rating_filter = request.GET.get('rating')
    if rating_filter:
        ratings = ratings.filter(rating=rating_filter)

    # Filter by featured status
    featured_filter = request.GET.get('featured')
    if featured_filter == 'true':
        ratings = ratings.filter(is_featured=True)
    elif featured_filter == 'false':
        ratings = ratings.filter(is_featured=False)

    context = {
        'ratings': ratings,
        'average_rating': rating_stats['average_rating'] or 0,
        'total_ratings': total_ratings,
        'distribution_list': distribution_list,
        'rating_filter': rating_filter,
        'featured_filter': featured_filter,
    }

    return render(request, 'admin/analytics/ratings.html', context)


