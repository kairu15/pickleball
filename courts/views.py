from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, OuterRef, Subquery, Avg, FloatField
from django.http import JsonResponse
from urllib.parse import urlencode
from datetime import datetime, timedelta, time

from accounts.decorators import admin_required
from .models import Site, Court, FavoriteCourt
from .forms import CourtForm, SiteForm
from dashboard.cache_utils import pages_cache_get_or_set
from dashboard.models import CourtPageSettings, FeaturedCourt, Rating
from reservations.models import Reservation


def court_list_view(request):
    rating_subq = Rating.objects.filter(
        reservation__court=OuterRef('pk')
    ).values('reservation__court').annotate(
        avg=Avg('rating')
    ).values('avg')

    courts = Court.objects.filter(is_active=True).select_related('site').annotate(
        rating_avg=Subquery(rating_subq, output_field=FloatField())
    )
    sites = Site.objects.filter(is_active=True)
    
    # Get CMS settings for the courts page (cached; invalidated via dashboard.cache_signals)
    cms_settings = pages_cache_get_or_set('court_list_cms', lambda: CourtPageSettings.objects.filter(pk=1, is_active=True).first())
    featured_courts = pages_cache_get_or_set('court_list_featured', lambda: list(
        FeaturedCourt.objects.select_related('court__site').filter(is_active=True).order_by('display_order')
    ))
    
    # ---- Filters ----
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
            reserved_ids = Reservation.objects.filter(
                date=selected_date,
                status__in=['confirmed', 'pending']
            ).values_list('court_id', flat=True)
            courts = courts.exclude(id__in=reserved_ids)
        except ValueError:
            pass
    
    search_query = request.GET.get('q', '').strip()
    if search_query:
        courts = courts.filter(
            Q(name__icontains=search_query) |
            Q(site__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    amenities_filter = request.GET.get('amenities', '').strip()
    if amenities_filter:
        courts = courts.filter(amenities__contains=[amenities_filter])
    
    # ---- Sorting ----
    sort = request.GET.get('sort', 'name')
    sort_map = {
        'name': 'name',
        '-name': '-name',
        'price': 'hourly_rate',
        '-price': '-hourly_rate',
        '-created_at': '-created_at',
        'created_at': 'created_at',
    }
    courts = courts.order_by(sort_map.get(sort, 'name'))
    
    # ---- Pagination ----
    paginator = Paginator(courts, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Build query string for pagination (preserve filters, remove page)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = '&' + query_params.urlencode() if query_params else ''

    return render(request, 'public/courts/court_list.html', {
        'courts': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'sites': sites,
        'selected_site': site_id,
        'selected_type': court_type,
        'selected_date': date,
        'search_query': search_query,
        'sort_by': sort,
        'query_string': query_string,
        'cms_settings': cms_settings,
        'featured_courts_cms': featured_courts,
    })


def _build_time_slots(court, slot_date, exclude_reservation_id=None):
    """Build 1-hour time slots (8 AM to 11 PM) for a court on a given date.
    Returns dicts with a 12-hour start time, AM/PM period, and a status of
    'available', 'booked' or 'unavailable'.

    Status priority: unavailable > booked > available.
    - unavailable: past slots on today, past dates, court under maintenance,
      court closed that weekday, or outside the court's operating schedule.
    - booked: overlaps a confirmed/pending reservation. Pass
      exclude_reservation_id when editing so the user's own booking is not
      counted as booked.
    - available: everything else.
    """
    reservations = list(Reservation.objects.filter(
        court=court,
        date=slot_date,
        status__in=['confirmed', 'pending']
    ).exclude(id=exclude_reservation_id))

    # Court operating schedule for that weekday (falls back to 8 AM - 11 PM)
    availability = court.availability.filter(day_of_week=slot_date.weekday()).first()
    court_closed = bool(availability and availability.is_closed)
    opening = availability.opening_time if availability else None
    closing = availability.closing_time if availability else None
    under_maintenance = court.status == 'maintenance'

    today = datetime.now().date()
    now_time = datetime.now().time()
    slots = []
    for hour in range(8, 24):
        end_hour = 23 if hour == 23 else hour + 1  # last slot ends at 11:59 PM
        end_minute = 59 if hour == 23 else 0
        slot_start, slot_end = time(hour, 0), time(end_hour, end_minute)
        is_booked = any(r.start_time < slot_end and r.end_time > slot_start for r in reservations)
        # 12-hour start time (e.g. '8:00 AM', '12:00 PM', '11:00 PM')
        period = 'AM' if hour < 12 else 'PM'
        hour12 = hour % 12 or 12
        # Past slots (today) and all slots on past dates can no longer be booked
        is_past = slot_date < today or (slot_date == today and time(hour, 0) <= now_time)
        # Closed day, maintenance, or outside the operating schedule
        is_outside_schedule = court_closed or under_maintenance or (
            opening and closing and (slot_start < opening or slot_end > closing)
        )
        if is_past or is_outside_schedule:
            status = 'unavailable'
        elif is_booked:
            status = 'booked'
        else:
            status = 'available'
        start_12h = f'{hour12}:00 {period}'
        end_12h_hour = end_hour % 12 or 12
        end_12h = f'{end_12h_hour}:{end_minute:02d} {"PM" if end_hour >= 12 else "AM"}'
        slots.append({
            'start': f'{hour:02d}:00',
            'end': f'{end_hour:02d}:{end_minute:02d}',
            'start_12h': start_12h,
            'period': period,
            'status': status,
            'available': status == 'available',
            'label': f'{start_12h} – {end_12h}',
        })
    return slots


def court_detail_view(request, court_id):
    court = get_object_or_404(Court.objects.select_related('site'), id=court_id, is_active=True)
    
    # Gallery images
    gallery_images = court.images.all()[:6]
    
    # Operating hours
    operating_hours = court.availability.all().order_by('day_of_week')
    
    # Upcoming reservations
    today = datetime.now().date()
    upcoming_reservations = Reservation.objects.filter(
        court=court,
        date__gte=today,
        status__in=['confirmed', 'pending']
    ).order_by('date', 'start_time')[:10]
    
    # Related courts (same site, excluding current)
    related_courts = Court.objects.filter(
        is_active=True,
        site=court.site
    ).exclude(
        id=court.id
    ).select_related('site').distinct()[:3]
    
    # Time slots for the selected date (defaults to today). Supports ?date=YYYY-MM-DD.
    date_param = request.GET.get('date', '')
    if date_param:
        try:
            selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    time_slots = _build_time_slots(court, selected_date)
    
    return render(request, 'public/courts/court_detail.html', {
        'court': court,
        'gallery_images': gallery_images,
        'operating_hours': operating_hours,
        'upcoming_reservations': upcoming_reservations,
        'related_courts': related_courts,
        'time_slots': time_slots,
        'selected_date': selected_date,
        'today': today,
    })


def court_directions_view(request, court_id):
    """Dedicated Get Directions page for a court.

    Embeds an interactive Leaflet map with keyless OSRM routing
    (driving / walking / cycling profiles), turn-by-turn steps,
    browser geolocation, and Google Maps / Waze fallback links."""
    court = get_object_or_404(
        Court.objects.select_related('site'),
        id=court_id, is_active=True
    )

    # Facility-level coordinates come from the site (court site)
    site = court.site
    has_coordinates = bool(site and site.latitude and site.longitude)
    latitude = float(site.latitude) if has_coordinates else None
    longitude = float(site.longitude) if has_coordinates else None

    # Operating hours for the court (by weekday)
    operating_hours = court.availability.all().order_by('day_of_week')

    # Primary image file: primary gallery image, else first gallery image, else court image
    gallery = court.images.all()
    primary = gallery.filter(is_primary=True).first() or gallery.first()
    court_image = primary.image if primary else court.image

    # Full address: site name (and description when available)
    full_address = site.name

    dest = f"{longitude},{latitude}" if has_coordinates else ''
    return render(request, 'public/courts/court_directions.html', {
        'court': court,
        'site': site,
        'court_image': court_image,
        'operating_hours': operating_hours,
        'full_address': full_address,
        'has_coordinates': has_coordinates,
        'latitude': latitude,
        'longitude': longitude,
        'google_maps_url': f'https://www.google.com/maps/dir/?api=1&destination={dest}' if has_coordinates else '',
        'waze_url': f'https://www.waze.com/ul?ll={latitude},{longitude}&navigate=yes' if has_coordinates else '',
    })


def court_availability_view(request, court_id):
    court = get_object_or_404(Court, id=court_id, is_active=True)
    
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    # Get reservations for the selected date
    reservations = Reservation.objects.filter(
        court=court,
        date=selected_date,
        status__in=['confirmed', 'pending']
    ).order_by('start_time')
    
    # Generate time slots (8 AM to 10 PM, 1-hour slots)
    time_slots = []
    start_hour = 8
    end_hour = 22
    
    for hour in range(start_hour, end_hour):
        slot_time = f"{hour:02d}:00"
        slot_end = f"{hour+1:02d}:00"
        
        # Check if this slot is reserved
        is_reserved = reservations.filter(
            start_time__lte=f"{hour:02d}:00",
            end_time__gt=f"{hour:02d}:00"
        ).exists()
        
        time_slots.append({
            'time': slot_time,
            'end_time': slot_end,
            'is_available': not is_reserved
        })
    
    return render(request, 'public/courts/availability.html', {
        'court': court,
        'selected_date': selected_date,
        'time_slots': time_slots
    })


def court_slots_api(request, court_id):
    """Public API: 1-hour time slots for a court on a given date (or today).
    Used by the Court Details page date picker to refresh availability without
    a page reload. Returns slots in 12-hour format with AM/PM period and status."""
    court = get_object_or_404(Court, id=court_id, is_active=True)
    date_str = request.GET.get('date', '')
    try:
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    return JsonResponse({
        'date': slot_date.isoformat(),
        'date_label': f"{slot_date.strftime('%A, %B')} {slot_date.day}, {slot_date.year}",
        'slots': _build_time_slots(court, slot_date),
    })


@login_required
def toggle_favorite_view(request, court_id):
    """AJAX view to toggle a court as favorite"""

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    court = get_object_or_404(Court, id=court_id, is_active=True)
    fav, created = FavoriteCourt.objects.get_or_create(user=request.user, court=court)

    if not created:
        fav.delete()
        return JsonResponse({'favorited': False, 'message': 'Removed from favorites'})

    return JsonResponse({'favorited': True, 'message': 'Added to favorites'})


@login_required
@admin_required
def admin_court_list_view(request):
    
    courts = Court.objects.select_related('site').all().order_by('-created_at')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        courts = courts.filter(
            Q(name__icontains=search_query) |
            Q(site__name__icontains=search_query) |
            Q(court_type__icontains=search_query)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        courts = courts.filter(is_active=True)
    elif status_filter == 'inactive':
        courts = courts.filter(is_active=False)
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    allowed_sort_fields = ['name', 'site__name', 'court_type', 'hourly_rate', 'created_at']
    if sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        courts = courts.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(courts, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/courts/court_list.html', {
        'courts': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
    })


@login_required
@admin_required
def admin_court_create_view(request):

    if request.method == 'POST':
        form = CourtForm(request.POST, request.FILES)
        if form.is_valid():
            created_court = form.save()
            messages.success(request, f'Court {created_court.name} created successfully.')
            return redirect('admin_court_list')
    else:
        form = CourtForm()
    
    return render(request, 'admin/courts/court_form.html', {
        'form': form,
        'edit_mode': False,
    })


@login_required
@admin_required
def admin_court_edit_view(request, court_id):

    court = get_object_or_404(Court.objects.all(), id=court_id)

    if request.method == 'POST':
        form = CourtForm(request.POST, request.FILES, instance=court)
        if form.is_valid():
            form.save()
            messages.success(request, f'Court {court.name} updated successfully.')
            return redirect('admin_court_list')
    else:
        form = CourtForm(instance=court)

    return render(request, 'admin/courts/court_form.html', {
        'form': form,
        'edit_mode': True,
        'court': court,
    })


@login_required
@admin_required
def admin_court_delete_view(request, court_id):
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_court_list')
    
    court = get_object_or_404(Court.objects.all(), id=court_id)
    
    if not court.is_active:
        messages.info(request, f'Court {court.name} is already inactive.')
        return redirect('admin_court_list')
    
    court.is_active = False
    court.save(update_fields=['is_active'])
    messages.success(request, f'Court {court.name} deactivated successfully.')
    return redirect('admin_court_list')


@login_required
@admin_required
def admin_site_list_view(request):
    
    sites = Site.objects.all().order_by('-created_at')
    
    return render(request, 'admin/sites/site_list.html', {'sites': sites})


@login_required
@admin_required
def admin_site_create_view(request):
    
    if request.method == 'POST':
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save()
            messages.success(request, 'Site created successfully.')
            return redirect('admin_site_list')
    else:
        form = SiteForm()
    
    return render(request, 'admin/sites/site_form.html', {'form': form, 'edit_mode': False})


@login_required
@admin_required
def admin_site_edit_view(request, site_id):
    
    site = get_object_or_404(Site.objects.all(), id=site_id)
    if request.method == 'POST':
        form = SiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, f'Site {site.name} updated successfully.')
            return redirect('admin_site_list')
    else:
        form = SiteForm(instance=site)
    
    return render(request, 'admin/sites/site_form.html', {'form': form, 'edit_mode': True, 'site': site})


@login_required
@admin_required
def admin_site_delete_view(request, site_id):
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_site_list')
    
    site = get_object_or_404(Site.objects.all(), id=site_id)
    site.delete()
    messages.success(request, f'Site {site.name} deleted successfully.')
    return redirect('admin_site_list')
