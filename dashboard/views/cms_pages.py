"""Courts / tournaments / equipment page CMS.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import super_admin_required
from dashboard.models import CourtPageSettings
from dashboard.models import EquipmentCategory
from dashboard.models import EquipmentPageSettings
from dashboard.models import FeaturedCourt
from dashboard.models import FeaturedEquipment
from dashboard.models import FeaturedTournament
from dashboard.models import TournamentAnnouncement
from dashboard.models import TournamentCategory
from dashboard.models import TournamentPageSettings
from dashboard.views.shared import _log_version
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render


@login_required
@super_admin_required
def courts_page_settings(request):
    """Edit courts page settings (singleton)."""
    settings, _ = CourtPageSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        old = {
            'hero_title': settings.hero_title,
            'hero_subtitle': settings.hero_subtitle,
        }
        settings.hero_title = request.POST.get('hero_title', 'Browse Courts')
        settings.hero_subtitle = request.POST.get('hero_subtitle', '')
        settings.page_title = request.POST.get('page_title', '')
        settings.meta_description = request.POST.get('meta_description', '')
        settings.show_search = request.POST.get('show_search') == 'on'
        settings.show_featured_first = request.POST.get('show_featured_first') == 'on'
        settings.featured_title = request.POST.get('featured_title', 'Featured Courts')
        settings.featured_subtitle = request.POST.get('featured_subtitle', '')
        settings.promo_banner_title = request.POST.get('promo_banner_title', '')
        settings.promo_banner_text = request.POST.get('promo_banner_text', '')
        settings.promo_banner_link = request.POST.get('promo_banner_link', '')
        settings.promo_banner_active = request.POST.get('promo_banner_active') == 'on'
        settings.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('banner_image'):
            settings.banner_image = request.FILES['banner_image']
        if request.FILES.get('promo_banner_image'):
            settings.promo_banner_image = request.FILES['promo_banner_image']

        settings.save()
        _log_version('courts', 'Page Settings', str(old), '', request.user)
        messages.success(request, 'Courts page settings updated successfully!')
        return redirect('super_admin_courts_cms')

    featured_courts = FeaturedCourt.objects.select_related('court').filter(is_active=True).order_by('display_order')

    return render(request, 'admin/cms/courts/settings.html', {
        'settings': settings,
        'featured_courts': featured_courts,
        'page_title': 'Courts Page CMS',
    })


@login_required
@super_admin_required
def courts_featured_add(request):
    """Add a featured court."""
    from courts.models import Court
    if request.method == 'POST':
        court_id = request.POST.get('court')
        label = request.POST.get('label', '')
        display_order = request.POST.get('display_order', 0)
        court = get_object_or_404(Court, id=court_id)
        FeaturedCourt.objects.create(
            court=court,
            label=label,
            display_order=display_order,
        )
        messages.success(request, f'Court "{court.name}" added to featured!')
        return redirect('super_admin_courts_cms')

    courts = Court.objects.filter(is_active=True).order_by('name')
    return render(request, 'admin/cms/courts/featured_form.html', {
        'courts': courts,
        'featured': None,
        'page_title': 'Add Featured Court',
    })


@login_required
@super_admin_required
def courts_featured_edit(request, featured_id):
    """Edit a featured court entry."""
    featured = get_object_or_404(FeaturedCourt, id=featured_id)
    from courts.models import Court
    if request.method == 'POST':
        court_id = request.POST.get('court')
        featured.court = get_object_or_404(Court, id=court_id)
        featured.label = request.POST.get('label', '')
        featured.display_order = request.POST.get('display_order', 0)
        featured.is_active = request.POST.get('is_active') == 'on'
        featured.save()
        messages.success(request, 'Featured court updated!')
        return redirect('super_admin_courts_cms')

    courts = Court.objects.filter(is_active=True).order_by('name')
    return render(request, 'admin/cms/courts/featured_form.html', {
        'courts': courts,
        'featured': featured,
        'page_title': 'Edit Featured Court',
    })


@login_required
@super_admin_required
def courts_featured_delete(request, featured_id):
    """Delete a featured court entry."""
    featured = get_object_or_404(FeaturedCourt, id=featured_id)
    if request.method == 'POST':
        featured.delete()
        messages.success(request, 'Featured court removed.')
        return redirect('super_admin_courts_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': featured,
        'cancel_url': 'super_admin_courts_cms',
    })


def tournaments_page_settings(request):
    """Edit tournaments page settings (singleton)."""
    settings, _ = TournamentPageSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.hero_title = request.POST.get('hero_title', 'Tournaments')
        settings.hero_subtitle = request.POST.get('hero_subtitle', '')
        settings.page_title = request.POST.get('page_title', '')
        settings.meta_description = request.POST.get('meta_description', '')
        settings.announcement = request.POST.get('announcement', '')
        settings.announcement_active = request.POST.get('announcement_active') == 'on'
        settings.featured_title = request.POST.get('featured_title', 'Featured Tournaments')
        settings.featured_subtitle = request.POST.get('featured_subtitle', '')
        settings.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('banner_image'):
            settings.banner_image = request.FILES['banner_image']
        settings.save()
        messages.success(request, 'Tournaments page settings updated!')
        return redirect('super_admin_tournaments_cms')

    categories = TournamentCategory.objects.filter(is_active=True).order_by('display_order')
    featured = FeaturedTournament.objects.select_related('tournament').filter(is_active=True).order_by('display_order')
    announcements = TournamentAnnouncement.objects.filter(is_active=True).order_by('display_order')

    return render(request, 'admin/cms/tournaments/settings.html', {
        'settings': settings,
        'categories': categories,
        'featured': featured,
        'announcements': announcements,
        'page_title': 'Tournaments Page CMS',
    })


@login_required
@super_admin_required
def tournament_category_add(request):
    if request.method == 'POST':
        TournamentCategory.objects.create(
            name=request.POST.get('name'),
            slug=request.POST.get('slug', ''),
            description=request.POST.get('description', ''),
            icon=request.POST.get('icon', 'fa-trophy'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'Tournament category created!')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/tournaments/category_form.html', {
        'category': None,
        'page_title': 'Add Tournament Category',
    })


@login_required
@super_admin_required
def tournament_category_edit(request, cat_id):
    cat = get_object_or_404(TournamentCategory, id=cat_id)
    if request.method == 'POST':
        cat.name = request.POST.get('name')
        cat.slug = request.POST.get('slug', '')
        cat.description = request.POST.get('description', '')
        cat.icon = request.POST.get('icon', 'fa-trophy')
        cat.display_order = request.POST.get('display_order', 0)
        cat.is_active = request.POST.get('is_active') == 'on'
        cat.save()
        messages.success(request, 'Tournament category updated!')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/tournaments/category_form.html', {
        'category': cat,
        'page_title': 'Edit Tournament Category',
    })


@login_required
@super_admin_required
def tournament_category_delete(request, cat_id):
    cat = get_object_or_404(TournamentCategory, id=cat_id)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Tournament category deleted.')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': cat,
        'cancel_url': 'super_admin_tournaments_cms',
    })


@login_required
@super_admin_required
def tournament_featured_add(request):
    from tournaments.models import Tournament
    if request.method == 'POST':
        t_id = request.POST.get('tournament')
        tournament = get_object_or_404(Tournament, id=t_id)
        FeaturedTournament.objects.create(
            tournament=tournament,
            label=request.POST.get('label', ''),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, f'"{tournament.name}" added to featured!')
        return redirect('super_admin_tournaments_cms')
    tournaments = Tournament.objects.all().order_by('-created_at')[:50]
    return render(request, 'admin/cms/tournaments/featured_form.html', {
        'tournaments': tournaments,
        'featured': None,
        'page_title': 'Add Featured Tournament',
    })


@login_required
@super_admin_required
def tournament_featured_edit(request, featured_id):
    featured = get_object_or_404(FeaturedTournament, id=featured_id)
    from tournaments.models import Tournament
    if request.method == 'POST':
        t_id = request.POST.get('tournament')
        featured.tournament = get_object_or_404(Tournament, id=t_id)
        featured.label = request.POST.get('label', '')
        featured.display_order = request.POST.get('display_order', 0)
        featured.is_active = request.POST.get('is_active') == 'on'
        featured.save()
        messages.success(request, 'Featured tournament updated!')
        return redirect('super_admin_tournaments_cms')
    tournaments = Tournament.objects.all().order_by('-created_at')[:50]
    return render(request, 'admin/cms/tournaments/featured_form.html', {
        'tournaments': tournaments,
        'featured': featured,
        'page_title': 'Edit Featured Tournament',
    })


@login_required
@super_admin_required
def tournament_featured_delete(request, featured_id):
    featured = get_object_or_404(FeaturedTournament, id=featured_id)
    if request.method == 'POST':
        featured.delete()
        messages.success(request, 'Featured tournament removed.')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': featured,
        'cancel_url': 'super_admin_tournaments_cms',
    })


@login_required
@super_admin_required
def tournament_announcement_add(request):
    if request.method == 'POST':
        TournamentAnnouncement.objects.create(
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            link_url=request.POST.get('link_url', ''),
            link_text=request.POST.get('link_text', 'Learn More'),
            announcement_type=request.POST.get('announcement_type', 'info'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'Announcement created!')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/tournaments/announcement_form.html', {
        'announcement': None,
        'announcement_types': TournamentAnnouncement._meta.get_field('announcement_type').choices,
        'page_title': 'New Tournament Announcement',
    })


@login_required
@super_admin_required
def tournament_announcement_edit(request, ann_id):
    ann = get_object_or_404(TournamentAnnouncement, id=ann_id)
    if request.method == 'POST':
        ann.title = request.POST.get('title')
        ann.message = request.POST.get('message')
        ann.link_url = request.POST.get('link_url', '')
        ann.link_text = request.POST.get('link_text', 'Learn More')
        ann.announcement_type = request.POST.get('announcement_type', 'info')
        ann.display_order = request.POST.get('display_order', 0)
        ann.is_active = request.POST.get('is_active') == 'on'
        ann.save()
        messages.success(request, 'Announcement updated!')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/tournaments/announcement_form.html', {
        'announcement': ann,
        'announcement_types': TournamentAnnouncement._meta.get_field('announcement_type').choices,
        'page_title': 'Edit Tournament Announcement',
    })


@login_required
@super_admin_required
def tournament_announcement_delete(request, ann_id):
    ann = get_object_or_404(TournamentAnnouncement, id=ann_id)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, 'Announcement deleted.')
        return redirect('super_admin_tournaments_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': ann,
        'cancel_url': 'super_admin_tournaments_cms',
    })


# ============================================================================
# EQUIPMENT PAGE CMS
# ============================================================================


@login_required
@super_admin_required
def equipment_page_settings(request):
    """Edit equipment page settings (singleton)."""
    settings, _ = EquipmentPageSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.hero_title = request.POST.get('hero_title', 'Equipment Rental')
        settings.hero_subtitle = request.POST.get('hero_subtitle', '')
        settings.page_title = request.POST.get('page_title', '')
        settings.meta_description = request.POST.get('meta_description', '')
        settings.featured_title = request.POST.get('featured_title', 'Featured Equipment')
        settings.featured_subtitle = request.POST.get('featured_subtitle', '')
        settings.show_availability_filter = request.POST.get('show_availability_filter') == 'on'
        settings.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('banner_image'):
            settings.banner_image = request.FILES['banner_image']
        settings.save()
        messages.success(request, 'Equipment page settings updated!')
        return redirect('super_admin_equipment_cms')

    categories = EquipmentCategory.objects.filter(is_active=True).order_by('display_order')
    featured = FeaturedEquipment.objects.select_related('equipment').filter(is_active=True).order_by('display_order')

    return render(request, 'admin/cms/equipment/settings.html', {
        'settings': settings,
        'categories': categories,
        'featured': featured,
        'page_title': 'Equipment Page CMS',
    })


@login_required
@super_admin_required
def equipment_category_add(request):
    if request.method == 'POST':
        EquipmentCategory.objects.create(
            name=request.POST.get('name'),
            slug=request.POST.get('slug', ''),
            description=request.POST.get('description', ''),
            icon=request.POST.get('icon', 'fa-tools'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'Equipment category created!')
        return redirect('super_admin_equipment_cms')
    return render(request, 'admin/cms/equipment/category_form.html', {
        'category': None,
        'page_title': 'Add Equipment Category',
    })


@login_required
@super_admin_required
def equipment_category_edit(request, cat_id):
    cat = get_object_or_404(EquipmentCategory, id=cat_id)
    if request.method == 'POST':
        cat.name = request.POST.get('name')
        cat.slug = request.POST.get('slug', '')
        cat.description = request.POST.get('description', '')
        cat.icon = request.POST.get('icon', 'fa-tools')
        cat.display_order = request.POST.get('display_order', 0)
        cat.is_active = request.POST.get('is_active') == 'on'
        cat.save()
        messages.success(request, 'Equipment category updated!')
        return redirect('super_admin_equipment_cms')
    return render(request, 'admin/cms/equipment/category_form.html', {
        'category': cat,
        'page_title': 'Edit Equipment Category',
    })


@login_required
@super_admin_required
def equipment_category_delete(request, cat_id):
    cat = get_object_or_404(EquipmentCategory, id=cat_id)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Equipment category deleted.')
        return redirect('super_admin_equipment_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': cat,
        'cancel_url': 'super_admin_equipment_cms',
    })


@login_required
@super_admin_required
def equipment_featured_add(request):
    from equipment.models import Equipment
    if request.method == 'POST':
        e_id = request.POST.get('equipment')
        equipment = get_object_or_404(Equipment, id=e_id)
        FeaturedEquipment.objects.create(
            equipment=equipment,
            label=request.POST.get('label', ''),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, f'"{equipment.name}" added to featured!')
        return redirect('super_admin_equipment_cms')
    equipment = Equipment.objects.filter(is_active=True).order_by('name')[:50]
    return render(request, 'admin/cms/equipment/featured_form.html', {
        'equipment_list': equipment,
        'featured': None,
        'page_title': 'Add Featured Equipment',
    })


@login_required
@super_admin_required
def equipment_featured_edit(request, featured_id):
    featured = get_object_or_404(FeaturedEquipment, id=featured_id)
    from equipment.models import Equipment
    if request.method == 'POST':
        e_id = request.POST.get('equipment')
        featured.equipment = get_object_or_404(Equipment, id=e_id)
        featured.label = request.POST.get('label', '')
        featured.display_order = request.POST.get('display_order', 0)
        featured.is_active = request.POST.get('is_active') == 'on'
        featured.save()
        messages.success(request, 'Featured equipment updated!')
        return redirect('super_admin_equipment_cms')
    equipment = Equipment.objects.filter(is_active=True).order_by('name')[:50]
    return render(request, 'admin/cms/equipment/featured_form.html', {
        'equipment_list': equipment,
        'featured': featured,
        'page_title': 'Edit Featured Equipment',
    })


@login_required
@super_admin_required
def equipment_featured_delete(request, featured_id):
    featured = get_object_or_404(FeaturedEquipment, id=featured_id)
    if request.method == 'POST':
        featured.delete()
        messages.success(request, 'Featured equipment removed.')
        return redirect('super_admin_equipment_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': featured,
        'cancel_url': 'super_admin_equipment_cms',
    })


# ============================================================================
# MAINTENANCE MODE
# ============================================================================
