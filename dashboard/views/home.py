"""Dashboard home / index / role redirects.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import staff_or_admin_required
from accounts.models import User
from accounts.models import UserActivity
from courts.models import Court
from courts.models import FavoriteCourt
from courts.models import Site
from dashboard.cache_utils import PAGES_CACHE_TIMEOUT
from dashboard.cache_utils import cache_anon_page
from dashboard.models import Amenity
from dashboard.models import GalleryImage
from dashboard.models import HomePageContent
from dashboard.models import Rating
from dashboard.models import SiteSettings
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.db.models import Count
from django.db.models import FloatField
from django.db.models import OuterRef
from django.db.models import Subquery
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from equipment.models import Equipment
from equipment.models import EquipmentRental
from math import atan2
from math import cos
from math import radians
from math import sin
from math import sqrt
from payments.models import Payment
from reservations.models import Reservation
from scoring.models import Match
from tournaments.models import Tournament


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
