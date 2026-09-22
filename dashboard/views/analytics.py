"""Super-admin reports, revenue analytics, exports and cache monitor.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import admin_required
from accounts.decorators import super_admin_required
from accounts.models import User
from courts.models import Court
from dashboard.cache_utils import PAGES_CACHE_TIMEOUT
from dashboard.models import Rating
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.db.models import Count
from django.db.models import Sum
from django.db.models.functions import ExtractHour
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from equipment.models import Equipment
from equipment.models import EquipmentRental
from payments.models import Payment
from reservations.models import Reservation
import csv


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
    from dashboard.cache_utils import get_cache_stats, get_invalidation_events, get_slow_queries

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
