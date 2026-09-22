"""
CMS Management Views for PickleSphere Super Admin
Handles CRUD operations for all dynamic page content.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import super_admin_required
from .models import (
    CourtPageSettings, FeaturedCourt,
    TournamentPageSettings, TournamentCategory, FeaturedTournament, TournamentAnnouncement,
    EquipmentPageSettings, EquipmentCategory, FeaturedEquipment,
    MaintenanceMode, MaintenanceAuditLog,
    SiteSettings, Partner, GlobalAnnouncement,
    ContentVersion,
    # NEW CMS Models
    HeroSectionSettings,
    SiteBranding,
    TopBarSettings,
    NavBarSettings, NavBarMenuItem,
    FooterSettings, FooterQuickLink,
    SocialPlatformSettings,
    # WEBSITE DESIGN CMS Models
    GlobalDesignSettings,
    ButtonStyleSettings,
    CardStyleSettings,
    ScrollToTopSettings,
)


# ============================================================================
# HELPER: Log content versions
# ============================================================================

def _log_version(content_type, section, old_value, new_value, user, is_published=True):
    """Log a content version entry."""
    last_version = ContentVersion.objects.filter(content_type=content_type).first()
    version_number = (last_version.version_number + 1) if last_version else 1
    ContentVersion.objects.create(
        content_type=content_type,
        section=section,
        old_value=str(old_value)[:5000],
        new_value=str(new_value)[:5000],
        changed_by=user,
        version_number=version_number,
        is_published=is_published,
    )


# ============================================================================
# COURTS PAGE CMS
# ============================================================================

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

@login_required
@super_admin_required
def maintenance_mode_settings(request):
    """Maintenance mode management page."""
    maintenance, _ = MaintenanceMode.objects.get_or_create(pk=1)
    logs = MaintenanceAuditLog.objects.all()[:50]

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'toggle':
            maintenance.is_active = not maintenance.is_active
            now = timezone.now()
            if maintenance.is_active:
                maintenance.last_enabled_at = now
                maintenance.last_enabled_by = request.user
                log_action = 'enabled'
                msg = 'Maintenance mode has been ENABLED.'
            else:
                maintenance.last_disabled_at = now
                maintenance.last_disabled_by = request.user
                log_action = 'disabled'
                msg = 'Maintenance mode has been DISABLED.'

            maintenance.save()

            MaintenanceAuditLog.objects.create(
                action=log_action,
                performed_by=request.user,
                details=f'Maintenance mode {"enabled" if maintenance.is_active else "disabled"} by {request.user.username}',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, msg)
            return redirect('super_admin_maintenance')

        elif action == 'update':
            maintenance.title = request.POST.get('title', 'System Under Maintenance')
            maintenance.message = request.POST.get('message', '')
            maintenance.estimated_return = request.POST.get('estimated_return') or None
            maintenance.show_contact_info = request.POST.get('show_contact_info') == 'on'
            maintenance.contact_email = request.POST.get('contact_email', '')
            maintenance.contact_phone = request.POST.get('contact_phone', '')
            maintenance.scheduled_start = request.POST.get('scheduled_start') or None
            maintenance.scheduled_end = request.POST.get('scheduled_end') or None
            if request.FILES.get('banner_image'):
                maintenance.banner_image = request.FILES['banner_image']
            maintenance.save()

            if maintenance.scheduled_start and maintenance.scheduled_end:
                MaintenanceAuditLog.objects.create(
                    action='scheduled',
                    performed_by=request.user,
                    details=f'Maintenance scheduled from {maintenance.scheduled_start} to {maintenance.scheduled_end}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                )

            _log_version('homepage', 'Maintenance Mode', '', '', request.user)
            messages.success(request, 'Maintenance settings updated!')
            return redirect('super_admin_maintenance')

    return render(request, 'admin/cms/maintenance/settings.html', {
        'maintenance': maintenance,
        'logs': logs,
        'page_title': 'Maintenance Mode',
    })


# ============================================================================
# SITE SETTINGS
# ============================================================================

@login_required
@super_admin_required
def site_settings_view(request):
    """Edit global site settings (singleton)."""
    settings, _ = SiteSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.footer_tagline = request.POST.get('footer_tagline', '')
        settings.footer_email = request.POST.get('footer_email', '')
        settings.footer_phone = request.POST.get('footer_phone', '')
        settings.footer_address = request.POST.get('footer_address', '')
        settings.copyright_text = request.POST.get('copyright_text', '')
        settings.override_stat_courts = request.POST.get('override_stat_courts') or None
        settings.override_stat_players = request.POST.get('override_stat_players') or None
        settings.override_stat_tournaments = request.POST.get('override_stat_tournaments') or None
        settings.override_stat_years = request.POST.get('override_stat_years') or None
        settings.partners_title = request.POST.get('partners_title', 'Our Partners')
        settings.partners_subtitle = request.POST.get('partners_subtitle', '')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()

        _log_version('homepage', 'Site Settings', '', '', request.user)
        messages.success(request, 'Site settings updated!')
        return redirect('super_admin_site_settings')

    partners = Partner.objects.filter(is_active=True).order_by('display_order')
    announcements = GlobalAnnouncement.objects.filter(is_active=True).order_by('display_order')

    return render(request, 'admin/cms/site/settings.html', {
        'settings': settings,
        'partners': partners,
        'announcements': announcements,
        'page_title': 'Site Settings',
    })


@login_required
@super_admin_required
def partner_add(request):
    if request.method == 'POST':
        partner = Partner(
            name=request.POST.get('name'),
            website_url=request.POST.get('website_url', ''),
            display_order=request.POST.get('display_order', 0),
        )
        if request.FILES.get('logo'):
            partner.logo = request.FILES['logo']
        partner.save()
        messages.success(request, 'Partner added!')
        return redirect('super_admin_site_settings')
    return render(request, 'admin/cms/site/partner_form.html', {
        'partner': None,
        'page_title': 'Add Partner',
    })


@login_required
@super_admin_required
def partner_edit(request, partner_id):
    partner = get_object_or_404(Partner, id=partner_id)
    if request.method == 'POST':
        partner.name = request.POST.get('name')
        partner.website_url = request.POST.get('website_url', '')
        partner.display_order = request.POST.get('display_order', 0)
        partner.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('logo'):
            partner.logo = request.FILES['logo']
        partner.save()
        messages.success(request, 'Partner updated!')
        return redirect('super_admin_site_settings')
    return render(request, 'admin/cms/site/partner_form.html', {
        'partner': partner,
        'page_title': 'Edit Partner',
    })


@login_required
@super_admin_required
def partner_delete(request, partner_id):
    partner = get_object_or_404(Partner, id=partner_id)
    if request.method == 'POST':
        partner.delete()
        messages.success(request, 'Partner removed.')
        return redirect('super_admin_site_settings')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': partner,
        'cancel_url': 'super_admin_site_settings',
    })


@login_required
@super_admin_required
def announcement_add(request):
    if request.method == 'POST':
        GlobalAnnouncement.objects.create(
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            announcement_type=request.POST.get('announcement_type', 'info'),
            link_url=request.POST.get('link_url', ''),
            link_text=request.POST.get('link_text', ''),
            show_on_pages=request.POST.get('show_on_pages', ''),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'Announcement created!')
        return redirect('super_admin_site_settings')
    return render(request, 'admin/cms/site/announcement_form.html', {
        'announcement': None,
        'announcement_types': GlobalAnnouncement._meta.get_field('announcement_type').choices,
        'page_title': 'New Announcement',
    })


@login_required
@super_admin_required
def announcement_edit(request, ann_id):
    ann = get_object_or_404(GlobalAnnouncement, id=ann_id)
    if request.method == 'POST':
        ann.title = request.POST.get('title')
        ann.message = request.POST.get('message')
        ann.announcement_type = request.POST.get('announcement_type', 'info')
        ann.link_url = request.POST.get('link_url', '')
        ann.link_text = request.POST.get('link_text', '')
        ann.show_on_pages = request.POST.get('show_on_pages', '')
        ann.display_order = request.POST.get('display_order', 0)
        ann.is_active = request.POST.get('is_active') == 'on'
        ann.save()
        messages.success(request, 'Announcement updated!')
        return redirect('super_admin_site_settings')
    return render(request, 'admin/cms/site/announcement_form.html', {
        'announcement': ann,
        'announcement_types': GlobalAnnouncement._meta.get_field('announcement_type').choices,
        'page_title': 'Edit Announcement',
    })


@login_required
@super_admin_required
def announcement_delete(request, ann_id):
    ann = get_object_or_404(GlobalAnnouncement, id=ann_id)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, 'Announcement deleted.')
        return redirect('super_admin_site_settings')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': ann,
        'cancel_url': 'super_admin_site_settings',
    })


# ============================================================================
# CONTENT VERSION HISTORY
# ============================================================================

@login_required
@super_admin_required
def content_version_list(request):
    """View content version history."""
    content_type = request.GET.get('content_type', '')
    versions = ContentVersion.objects.select_related('changed_by').all()

    if content_type:
        versions = versions.filter(content_type=content_type)

    versions = versions[:100]

    return render(request, 'admin/cms/versions/list.html', {
        'versions': versions,
        'selected_type': content_type,
        'content_type_choices': ContentVersion.CONTENT_TYPE_CHOICES,
        'page_title': 'Content Version History',
    })


# ============================================================================
# FAQ PAGE CMS
# ============================================================================

@login_required
@super_admin_required
def faq_cms_settings(request):
    """FAQ page CMS management."""
    from .models import FAQPageContent, FAQCategory, FAQItem

    content = FAQPageContent.objects.filter(is_active=True).order_by('section')
    categories = FAQCategory.objects.filter(is_active=True).order_by('display_order')
    items = FAQItem.objects.select_related('category').filter(is_active=True).order_by('display_order')

    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        if section and content_text:
            obj, created = FAQPageContent.objects.update_or_create(
                section=section,
                defaults={'content': content_text, 'is_active': True}
            )
            _log_version('homepage', f'FAQ Content - {section}', '', content_text, request.user)
            messages.success(request, 'FAQ content updated!')
        return redirect('super_admin_faq_cms')

    return render(request, 'admin/cms/faq/settings.html', {
        'content': content,
        'categories': categories,
        'items': items,
        'section_choices': FAQPageContent.SECTION_CHOICES,
        'page_title': 'FAQ Page CMS',
    })


@login_required
@super_admin_required
def faq_category_add(request):
    from .models import FAQCategory
    if request.method == 'POST':
        FAQCategory.objects.create(
            name=request.POST.get('name'),
            icon=request.POST.get('icon', 'fa-question-circle'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'FAQ category created!')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/faq/category_form.html', {
        'category': None,
        'page_title': 'Add FAQ Category',
    })


@login_required
@super_admin_required
def faq_category_edit(request, cat_id):
    from .models import FAQCategory
    cat = get_object_or_404(FAQCategory, id=cat_id)
    if request.method == 'POST':
        cat.name = request.POST.get('name')
        cat.icon = request.POST.get('icon', 'fa-question-circle')
        cat.display_order = request.POST.get('display_order', 0)
        cat.is_active = request.POST.get('is_active') == 'on'
        cat.save()
        messages.success(request, 'FAQ category updated!')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/faq/category_form.html', {
        'category': cat,
        'page_title': 'Edit FAQ Category',
    })


@login_required
@super_admin_required
def faq_category_delete(request, cat_id):
    from .models import FAQCategory
    cat = get_object_or_404(FAQCategory, id=cat_id)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'FAQ category deleted.')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': cat,
        'cancel_url': 'super_admin_faq_cms',
    })


@login_required
@super_admin_required
def faq_item_add(request):
    from .models import FAQCategory, FAQItem
    if request.method == 'POST':
        category_id = request.POST.get('category')
        FAQItem.objects.create(
            category=get_object_or_404(FAQCategory, id=category_id),
            question=request.POST.get('question'),
            answer=request.POST.get('answer'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'FAQ item created!')
        return redirect('super_admin_faq_cms')
    categories = FAQCategory.objects.filter(is_active=True).order_by('display_order')
    return render(request, 'admin/cms/faq/item_form.html', {
        'item': None,
        'categories': categories,
        'page_title': 'Add FAQ Item',
    })


@login_required
@super_admin_required
def faq_item_edit(request, item_id):
    from .models import FAQCategory, FAQItem
    item = get_object_or_404(FAQItem, id=item_id)
    if request.method == 'POST':
        category_id = request.POST.get('category')
        item.category = get_object_or_404(FAQCategory, id=category_id)
        item.question = request.POST.get('question')
        item.answer = request.POST.get('answer')
        item.display_order = request.POST.get('display_order', 0)
        item.is_active = request.POST.get('is_active') == 'on'
        item.save()
        messages.success(request, 'FAQ item updated!')
        return redirect('super_admin_faq_cms')
    categories = FAQCategory.objects.filter(is_active=True).order_by('display_order')
    return render(request, 'admin/cms/faq/item_form.html', {
        'item': item,
        'categories': categories,
        'page_title': 'Edit FAQ Item',
    })


@login_required
@super_admin_required
def faq_item_delete(request, item_id):
    from .models import FAQItem
    item = get_object_or_404(FAQItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'FAQ item deleted.')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': item,
        'cancel_url': 'super_admin_faq_cms',
    })


# ============================================================================
# TERMS OF SERVICE CMS
# ============================================================================

@login_required
@super_admin_required
def terms_cms_settings(request):
    """Terms of Service page CMS."""
    from .models import TermsContent, TermsSection
    content = TermsContent.objects.filter(is_active=True).order_by('section')
    sections = TermsSection.objects.filter(is_active=True).order_by('section_number')

    if request.method == 'POST' and request.POST.get('section'):
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        obj, created = TermsContent.objects.update_or_create(
            section=section,
            defaults={'content': content_text, 'is_active': True}
        )
        _log_version('homepage', f'Terms Content - {section}', '', content_text, request.user)
        messages.success(request, 'Terms content updated!')
        return redirect('super_admin_terms_cms')

    return render(request, 'admin/cms/terms/settings.html', {
        'content': content,
        'sections': sections,
        'section_choices': TermsContent.SECTION_CHOICES,
        'page_title': 'Terms of Service CMS',
    })


@login_required
@super_admin_required
def terms_section_add(request):
    from .models import TermsSection
    if request.method == 'POST':
        TermsSection.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            icon=request.POST.get('icon', 'fa-file-contract'),
            icon_color=request.POST.get('icon_color', 'primary'),
            section_number=request.POST.get('section_number', 1),
        )
        messages.success(request, 'Terms section created!')
        return redirect('super_admin_terms_cms')
    return render(request, 'admin/cms/terms/section_form.html', {
        'section': None,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Add Terms Section',
    })


@login_required
@super_admin_required
def terms_section_edit(request, section_id):
    from .models import TermsSection
    sec = get_object_or_404(TermsSection, id=section_id)
    if request.method == 'POST':
        sec.title = request.POST.get('title')
        sec.content = request.POST.get('content')
        sec.icon = request.POST.get('icon', 'fa-file-contract')
        sec.icon_color = request.POST.get('icon_color', 'primary')
        sec.section_number = request.POST.get('section_number', 1)
        sec.is_active = request.POST.get('is_active') == 'on'
        sec.save()
        messages.success(request, 'Terms section updated!')
        return redirect('super_admin_terms_cms')
    return render(request, 'admin/cms/terms/section_form.html', {
        'section': sec,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Terms Section',
    })


@login_required
@super_admin_required
def terms_section_delete(request, section_id):
    from .models import TermsSection
    sec = get_object_or_404(TermsSection, id=section_id)
    if request.method == 'POST':
        sec.delete()
        messages.success(request, 'Terms section deleted.')
        return redirect('super_admin_terms_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': sec,
        'cancel_url': 'super_admin_terms_cms',
    })


# ============================================================================
# PRIVACY POLICY CMS
# ============================================================================

@login_required
@super_admin_required
def privacy_cms_settings(request):
    """Privacy Policy page CMS."""
    from .models import PrivacyContent, PrivacySection
    content = PrivacyContent.objects.filter(is_active=True).order_by('section')
    sections = PrivacySection.objects.filter(is_active=True).order_by('section_number')

    if request.method == 'POST' and request.POST.get('section'):
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        obj, created = PrivacyContent.objects.update_or_create(
            section=section,
            defaults={'content': content_text, 'is_active': True}
        )
        _log_version('homepage', f'Privacy Content - {section}', '', content_text, request.user)
        messages.success(request, 'Privacy content updated!')
        return redirect('super_admin_privacy_cms')

    return render(request, 'admin/cms/privacy/settings.html', {
        'content': content,
        'sections': sections,
        'section_choices': PrivacyContent.SECTION_CHOICES,
        'page_title': 'Privacy Policy CMS',
    })


@login_required
@super_admin_required
def privacy_section_add(request):
    from .models import PrivacySection
    if request.method == 'POST':
        PrivacySection.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            icon=request.POST.get('icon', 'fa-shield-alt'),
            icon_color=request.POST.get('icon_color', 'primary'),
            section_number=request.POST.get('section_number', 1),
        )
        messages.success(request, 'Privacy section created!')
        return redirect('super_admin_privacy_cms')
    return render(request, 'admin/cms/privacy/section_form.html', {
        'section': None,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Add Privacy Section',
    })


@login_required
@super_admin_required
def privacy_section_edit(request, section_id):
    from .models import PrivacySection
    sec = get_object_or_404(PrivacySection, id=section_id)
    if request.method == 'POST':
        sec.title = request.POST.get('title')
        sec.content = request.POST.get('content')
        sec.icon = request.POST.get('icon', 'fa-shield-alt')
        sec.icon_color = request.POST.get('icon_color', 'primary')
        sec.section_number = request.POST.get('section_number', 1)
        sec.is_active = request.POST.get('is_active') == 'on'
        sec.save()
        messages.success(request, 'Privacy section updated!')
        return redirect('super_admin_privacy_cms')
    return render(request, 'admin/cms/privacy/section_form.html', {
        'section': sec,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Privacy Section',
    })


@login_required
@super_admin_required
def privacy_section_delete(request, section_id):
    from .models import PrivacySection
    sec = get_object_or_404(PrivacySection, id=section_id)
    if request.method == 'POST':
        sec.delete()
        messages.success(request, 'Privacy section deleted.')
        return redirect('super_admin_privacy_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': sec,
        'cancel_url': 'super_admin_privacy_cms',
    })


# ============================================================================
# MEDIA LIBRARY
# ============================================================================

@login_required
@super_admin_required
def media_library_view(request):
    """Media library management page."""
    from .models import MediaLibrary
    media_type = request.GET.get('type', '')
    q = request.GET.get('q', '')
    media = MediaLibrary.objects.all().order_by('-created_at')

    if media_type:
        media = media.filter(file_type=media_type)
    if q:
        media = media.filter(title__icontains=q)

    return render(request, 'admin/cms/media/list.html', {
        'media': media,
        'media_type': media_type,
        'q': q,
        'page_title': 'Media Library',
    })


@login_required
@super_admin_required
def media_library_upload(request):
    """Upload media file."""
    from .models import MediaLibrary
    if request.method == 'POST':
        title = request.POST.get('title')
        file = request.FILES.get('file')
        alt_text = request.POST.get('alt_text', '')
        caption = request.POST.get('caption', '')

        if title and file:
            media = MediaLibrary.objects.create(
                title=title,
                file=file,
                alt_text=alt_text,
                caption=caption,
                uploaded_by=request.user,
            )
            messages.success(request, f'"{media.title}" uploaded successfully!')
            return redirect('super_admin_media_library')
        else:
            messages.error(request, 'Please provide a title and select a file.')

    return render(request, 'admin/cms/media/upload.html', {
        'page_title': 'Upload Media',
    })


@login_required
@super_admin_required
def media_library_edit(request, media_id):
    """Edit media library item."""
    from .models import MediaLibrary
    media = get_object_or_404(MediaLibrary, id=media_id)
    if request.method == 'POST':
        media.title = request.POST.get('title')
        media.alt_text = request.POST.get('alt_text', '')
        media.caption = request.POST.get('caption', '')
        media.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('file'):
            media.file = request.FILES['file']
        media.save()
        messages.success(request, 'Media item updated!')
        return redirect('super_admin_media_library')
    return render(request, 'admin/cms/media/edit.html', {
        'media': media,
        'page_title': 'Edit Media',
    })


@login_required
@super_admin_required
def media_library_delete(request, media_id):
    """Delete media library item."""
    from .models import MediaLibrary
    media = get_object_or_404(MediaLibrary, id=media_id)
    if request.method == 'POST':
        media.delete()
        messages.success(request, 'Media item deleted.')
        return redirect('super_admin_media_library')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': media,
        'cancel_url': 'super_admin_media_library',
    })


# ============================================================================
# HERO SECTION CMS
# ============================================================================

@login_required
@super_admin_required
def hero_section_settings(request):
    """Hero section settings management (singleton)."""
    settings, _ = HeroSectionSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.background_type = request.POST.get('background_type', 'gradient')
        settings.solid_color = request.POST.get('solid_color', '#1a3a42')
        settings.gradient_start = request.POST.get('gradient_start', '#1a3a42')
        settings.gradient_end = request.POST.get('gradient_end', '#0f172a')
        settings.gradient_direction = request.POST.get('gradient_direction', '135deg')
        settings.overlay_color = request.POST.get('overlay_color', '#000000')
        try:
            settings.overlay_opacity = float(request.POST.get('overlay_opacity', 0.6))
        except ValueError:
            settings.overlay_opacity = 0.6
        settings.badge_text = request.POST.get('badge_text', '')
        settings.title = request.POST.get('title', 'Welcome to PickleSphere')
        settings.subtitle = request.POST.get('subtitle', '')
        settings.show_search_widget = request.POST.get('show_search_widget') == 'on'
        settings.min_height = request.POST.get('min_height', '90vh')
        settings.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('background_image'):
            settings.background_image = request.FILES['background_image']
        settings.save()
        _log_version('hero', 'Hero Section', '', '', request.user)
        messages.success(request, 'Hero section settings updated!')
        return redirect('super_admin_hero_cms')

    return render(request, 'admin/cms/hero/settings.html', {
        'settings': settings,
        'page_title': 'Hero Section CMS',
    })


@login_required
@super_admin_required
def hero_section_preview(request):
    """Return JSON hero preview data for live preview."""
    from django.http import JsonResponse
    settings, _ = HeroSectionSettings.objects.get_or_create(pk=1)
    return JsonResponse({
        'background_style': settings.get_background_style(),
        'badge_text': settings.badge_text,
        'title': settings.title,
        'subtitle': settings.subtitle,
        'show_search_widget': settings.show_search_widget,
        'min_height': settings.min_height,
    })


# ============================================================================
# WEBSITE BRANDING CMS
# ============================================================================

@login_required
@super_admin_required
def site_branding_settings(request):
    """Website branding management (logos, favicon)."""
    branding, _ = SiteBranding.objects.get_or_create(pk=1)

    if request.method == 'POST':
        branding.brand_name = request.POST.get('brand_name', 'PickleSphere')
        branding.is_active = request.POST.get('is_active') == 'on'
        logo_fields = ['website_logo', 'header_logo', 'footer_logo', 'favicon', 'login_logo', 'loading_logo', 'email_logo']
        for field in logo_fields:
            if request.FILES.get(field):
                setattr(branding, field, request.FILES[field])
        branding.save()
        _log_version('branding', 'Site Branding', '', '', request.user)
        messages.success(request, 'Branding updated successfully! Changes will appear on the website immediately.')
        return redirect('super_admin_branding_cms')

    return render(request, 'admin/cms/branding/settings.html', {
        'branding': branding,
        'page_title': 'Website Branding',
    })


@login_required
@super_admin_required
def site_branding_remove_logo(request, logo_field):
    """Remove a specific logo image."""
    branding, _ = SiteBranding.objects.get_or_create(pk=1)
    allowed_fields = ['website_logo', 'header_logo', 'footer_logo', 'favicon', 'login_logo', 'loading_logo', 'email_logo']
    if logo_field in allowed_fields and hasattr(branding, logo_field):
        setattr(branding, logo_field, None)
        branding.save()
        messages.success(request, f'{logo_field.replace("_", " ").title()} removed.')
    return redirect('super_admin_branding_cms')


@login_required
@super_admin_required
def site_branding_restore_defaults(request):
    """Restore all branding defaults."""
    branding, _ = SiteBranding.objects.get_or_create(pk=1)
    if request.method == 'POST':
        branding.website_logo = None
        branding.header_logo = None
        branding.footer_logo = None
        branding.favicon = None
        branding.login_logo = None
        branding.loading_logo = None
        branding.email_logo = None
        branding.brand_name = 'PickleSphere'
        branding.save()
        messages.success(request, 'All branding defaults restored.')
        return redirect('super_admin_branding_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': branding,
        'cancel_url': 'super_admin_branding_cms',
        'message': 'Are you sure you want to restore all branding to defaults? All uploaded logos will be removed.',
    })


# ============================================================================
# TOP BAR CMS
# ============================================================================

@login_required
@super_admin_required
def topbar_settings(request):
    """Top bar settings management (singleton)."""
    settings, _ = TopBarSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.is_visible = request.POST.get('is_visible') == 'on'
        settings.show_contact_info = request.POST.get('show_contact_info') == 'on'
        settings.show_social_media = request.POST.get('show_social_media') == 'on'
        settings.show_language_selector = request.POST.get('show_language_selector') == 'on'
        settings.phone_primary = request.POST.get('phone_primary', '')
        settings.phone_secondary = request.POST.get('phone_secondary', '')
        settings.email_primary = request.POST.get('email_primary', '')
        settings.email_secondary = request.POST.get('email_secondary', '')
        settings.office_hours = request.POST.get('office_hours', '')
        settings.physical_address = request.POST.get('physical_address', '')
        settings.background_color = request.POST.get('background_color', '#1a3a42')
        settings.background_gradient_start = request.POST.get('background_gradient_start', '#1a3a42')
        settings.background_gradient_end = request.POST.get('background_gradient_end', '#0f172a')
        settings.text_color = request.POST.get('text_color', 'rgba(255,255,255,0.85)')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('topbar', 'Top Bar Settings', '', '', request.user)
        messages.success(request, 'Top bar settings updated!')
        return redirect('super_admin_topbar_cms')

    return render(request, 'admin/cms/topbar/settings.html', {
        'settings': settings,
        'page_title': 'Top Bar CMS',
    })


# ============================================================================
# NAVIGATION BAR CMS
# ============================================================================

@login_required
@super_admin_required
def navbar_settings(request):
    """Navbar settings management + menu items list."""
    settings, _ = NavBarSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.is_sticky = request.POST.get('is_sticky') == 'on'
        settings.show_brand = request.POST.get('show_brand') == 'on'
        settings.brand_text = request.POST.get('brand_text', 'PickleSphere')
        settings.background_color = request.POST.get('background_color', '#0f172a')
        settings.text_color = request.POST.get('text_color', 'rgba(255,255,255,0.8)')
        settings.text_color_hover = request.POST.get('text_color_hover', '#ffffff')
        settings.cta_button_text = request.POST.get('cta_button_text', 'Get Started')
        settings.cta_button_color = request.POST.get('cta_button_color', '#3B7A8C')
        settings.show_search = request.POST.get('show_search') == 'on'
        settings.container_style = request.POST.get('container_style', 'container')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('navbar', 'NavBar Settings', '', '', request.user)
        messages.success(request, 'Navigation bar settings updated!')
        return redirect('super_admin_navbar_cms')

    menu_items = NavBarMenuItem.objects.all().order_by('menu_position', 'display_order')

    return render(request, 'admin/cms/navbar/settings.html', {
        'settings': settings,
        'menu_items': menu_items,
        'link_type_choices': NavBarMenuItem.LINK_TYPE_CHOICES,
        'page_title': 'Navigation Bar CMS',
    })


@login_required
@super_admin_required
def navbar_menu_item_add(request):
    if request.method == 'POST':
        NavBarMenuItem.objects.create(
            title=request.POST.get('title'),
            link_type=request.POST.get('link_type', 'custom'),
            custom_url=request.POST.get('custom_url', ''),
            menu_position=request.POST.get('menu_position', 'left'),
            requires_auth=request.POST.get('requires_auth') == 'on',
            hide_if_auth=request.POST.get('hide_if_auth') == 'on',
            open_in_new_tab=request.POST.get('open_in_new_tab') == 'on',
            icon_class=request.POST.get('icon_class', ''),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'Menu item created!')
        return redirect('super_admin_navbar_cms')
    return render(request, 'admin/cms/navbar/menu_item_form.html', {
        'item': None,
        'link_type_choices': NavBarMenuItem.LINK_TYPE_CHOICES,
        'page_title': 'Add Menu Item',
    })


@login_required
@super_admin_required
def navbar_menu_item_edit(request, item_id):
    item = get_object_or_404(NavBarMenuItem, id=item_id)
    if request.method == 'POST':
        item.title = request.POST.get('title')
        item.link_type = request.POST.get('link_type', 'custom')
        item.custom_url = request.POST.get('custom_url', '')
        item.menu_position = request.POST.get('menu_position', 'left')
        item.requires_auth = request.POST.get('requires_auth') == 'on'
        item.hide_if_auth = request.POST.get('hide_if_auth') == 'on'
        item.open_in_new_tab = request.POST.get('open_in_new_tab') == 'on'
        item.icon_class = request.POST.get('icon_class', '')
        item.display_order = request.POST.get('display_order', 0)
        item.is_active = request.POST.get('is_active') == 'on'
        item.save()
        messages.success(request, 'Menu item updated!')
        return redirect('super_admin_navbar_cms')
    return render(request, 'admin/cms/navbar/menu_item_form.html', {
        'item': item,
        'link_type_choices': NavBarMenuItem.LINK_TYPE_CHOICES,
        'page_title': 'Edit Menu Item',
    })


@login_required
@super_admin_required
def navbar_menu_item_delete(request, item_id):
    item = get_object_or_404(NavBarMenuItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Menu item deleted.')
        return redirect('super_admin_navbar_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': item,
        'cancel_url': 'super_admin_navbar_cms',
    })


# ============================================================================
# FOOTER CMS
# ============================================================================

@login_required
@super_admin_required
def footer_settings(request):
    """Footer settings + quick links management."""
    settings, _ = FooterSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.is_visible = request.POST.get('is_visible') == 'on'
        settings.organization_name = request.POST.get('organization_name', 'PickleSphere')
        settings.short_description = request.POST.get('short_description', '')
        settings.copyright_text = request.POST.get('copyright_text', '')
        settings.show_newsletter = request.POST.get('show_newsletter') == 'on'
        settings.newsletter_heading = request.POST.get('newsletter_heading', 'Newsletter')
        settings.newsletter_description = request.POST.get('newsletter_description', '')
        settings.newsletter_button_text = request.POST.get('newsletter_button_text', 'Subscribe')
        settings.show_social_media = request.POST.get('show_social_media') == 'on'
        settings.show_contact_details = request.POST.get('show_contact_details') == 'on'
        settings.show_quick_links = request.POST.get('show_quick_links') == 'on'
        settings.developer_credit = request.POST.get('developer_credit', '')
        settings.developer_contact = request.POST.get('developer_contact', '')
        settings.version_text = request.POST.get('version_text', '')
        settings.background_gradient_start = request.POST.get('background_gradient_start', '#1a3a42')
        settings.background_gradient_end = request.POST.get('background_gradient_end', '#0d1f23')
        settings.text_color = request.POST.get('text_color', 'rgba(255,255,255,0.7)')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('footer', 'Footer Settings', '', '', request.user)
        messages.success(request, 'Footer settings updated!')
        return redirect('super_admin_footer_cms')

    quick_links = FooterQuickLink.objects.filter(is_active=True).order_by('display_order')

    return render(request, 'admin/cms/footer/settings.html', {
        'settings': settings,
        'quick_links': quick_links,
        'page_title': 'Footer CMS',
    })


@login_required
@super_admin_required
def footer_quick_link_add(request):
    if request.method == 'POST':
        FooterQuickLink.objects.create(
            title=request.POST.get('title'),
            link_type=request.POST.get('link_type', 'custom'),
            custom_url=request.POST.get('custom_url', ''),
            open_in_new_tab=request.POST.get('open_in_new_tab') == 'on',
            icon_class=request.POST.get('icon_class', ''),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'Quick link created!')
        return redirect('super_admin_footer_cms')
    return render(request, 'admin/cms/footer/quick_link_form.html', {
        'link': None,
        'link_type_choices': FooterQuickLink.LINK_TYPE_CHOICES,
        'page_title': 'Add Quick Link',
    })


@login_required
@super_admin_required
def footer_quick_link_edit(request, link_id):
    link = get_object_or_404(FooterQuickLink, id=link_id)
    if request.method == 'POST':
        link.title = request.POST.get('title')
        link.link_type = request.POST.get('link_type', 'custom')
        link.custom_url = request.POST.get('custom_url', '')
        link.open_in_new_tab = request.POST.get('open_in_new_tab') == 'on'
        link.icon_class = request.POST.get('icon_class', '')
        link.display_order = request.POST.get('display_order', 0)
        link.is_active = request.POST.get('is_active') == 'on'
        link.save()
        messages.success(request, 'Quick link updated!')
        return redirect('super_admin_footer_cms')
    return render(request, 'admin/cms/footer/quick_link_form.html', {
        'link': link,
        'link_type_choices': FooterQuickLink.LINK_TYPE_CHOICES,
        'page_title': 'Edit Quick Link',
    })


@login_required
@super_admin_required
def footer_quick_link_delete(request, link_id):
    link = get_object_or_404(FooterQuickLink, id=link_id)
    if request.method == 'POST':
        link.delete()
        messages.success(request, 'Quick link deleted.')
        return redirect('super_admin_footer_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': link,
        'cancel_url': 'super_admin_footer_cms',
    })


# ============================================================================
# SOCIAL MEDIA PLATFORM SETTINGS CMS
# ============================================================================

@login_required
@super_admin_required
def social_media_settings(request):
    """Social media platform management."""
    platforms = SocialPlatformSettings.objects.all().order_by('display_order')

    if request.method == 'POST':
        # Create default entries for platforms that don't exist yet
        default_platforms = ['facebook', 'twitter', 'instagram', 'whatsapp', 'linkedin', 'youtube', 'tiktok']
        for p in default_platforms:
            SocialPlatformSettings.objects.get_or_create(platform=p)
        messages.success(request, 'Default social platforms initialized!')
        return redirect('super_admin_social_cms')

    return render(request, 'admin/cms/social/settings.html', {
        'platforms': platforms,
        'page_title': 'Social Media CMS',
    })


@login_required
@super_admin_required
def social_platform_edit(request, platform_id):
    platform = get_object_or_404(SocialPlatformSettings, id=platform_id)
    if request.method == 'POST':
        platform.url = request.POST.get('url', '')
        platform.is_active = request.POST.get('is_active') == 'on'
        platform.show_in_topbar = request.POST.get('show_in_topbar') == 'on'
        platform.show_in_footer = request.POST.get('show_in_footer') == 'on'
        platform.open_in_new_tab = request.POST.get('open_in_new_tab') == 'on'
        platform.display_order = request.POST.get('display_order', 0)
        platform.save()
        messages.success(request, f'{platform.get_platform_display()} settings updated!')
        return redirect('super_admin_social_cms')
    return render(request, 'admin/cms/social/platform_form.html', {
        'platform': platform,
        'page_title': f'Edit {platform.get_platform_display()}',
    })


# ============================================================================
# GLOBAL DESIGN SETTINGS CMS
# ============================================================================

@login_required
@super_admin_required
def global_design_settings(request):
    """Global design system settings (singleton)."""
    settings, _ = GlobalDesignSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.heading_font_family = request.POST.get('heading_font_family', "'Inter', -apple-system, BlinkMacSystemFont, sans-serif")
        settings.body_font_family = request.POST.get('body_font_family', "'Inter', -apple-system, BlinkMacSystemFont, sans-serif")
        settings.base_font_size = request.POST.get('base_font_size', '16px')
        settings.heading_font_weight = request.POST.get('heading_font_weight', '700')
        settings.primary_color = request.POST.get('primary_color', '#3B7A8C')
        settings.primary_hover_color = request.POST.get('primary_hover_color', '#2d5f6e')
        settings.secondary_color = request.POST.get('secondary_color', '#1a3a42')
        settings.accent_color = request.POST.get('accent_color', '#4A9DA8')
        settings.success_color = request.POST.get('success_color', '#28a745')
        settings.warning_color = request.POST.get('warning_color', '#ffc107')
        settings.danger_color = request.POST.get('danger_color', '#dc3545')
        settings.info_color = request.POST.get('info_color', '#17a2b8')
        settings.text_primary_color = request.POST.get('text_primary_color', '#212529')
        settings.text_muted_color = request.POST.get('text_muted_color', '#6c757d')
        settings.background_light_color = request.POST.get('background_light_color', '#f8f9fa')
        settings.background_dark_color = request.POST.get('background_dark_color', '#0f172a')
        settings.border_radius_sm = request.POST.get('border_radius_sm', '6px')
        settings.border_radius_md = request.POST.get('border_radius_md', '12px')
        settings.border_radius_lg = request.POST.get('border_radius_lg', '20px')
        settings.border_radius_full = request.POST.get('border_radius_full', '50px')
        settings.shadow_sm = request.POST.get('shadow_sm', '0 2px 8px rgba(0,0,0,0.05)')
        settings.shadow_md = request.POST.get('shadow_md', '0 4px 16px rgba(0,0,0,0.08)')
        settings.shadow_lg = request.POST.get('shadow_lg', '0 8px 30px rgba(0,0,0,0.12)')
        settings.spacing_unit = request.POST.get('spacing_unit', '8px')
        settings.section_padding = request.POST.get('section_padding', '5rem 0')
        settings.container_max_width = request.POST.get('container_max_width', '1200px')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('homepage', 'Global Design Settings', '', '', request.user)
        messages.success(request, 'Global design settings updated!')
        return redirect('super_admin_global_design')

    return render(request, 'admin/cms/design/global_settings.html', {
        'settings': settings,
        'page_title': 'Global Design System',
    })


# ============================================================================
# BUTTON STYLE SETTINGS CMS
# ============================================================================

@login_required
@super_admin_required
def button_style_settings(request):
    """Button style settings (singleton)."""
    settings, _ = ButtonStyleSettings.objects.get_or_create(pk=1)
    global_settings, _ = GlobalDesignSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.button_border_radius = request.POST.get('button_border_radius', '8px')
        settings.button_padding_y = request.POST.get('button_padding_y', '0.625rem')
        settings.button_padding_x = request.POST.get('button_padding_x', '1.5rem')
        settings.button_font_weight = request.POST.get('button_font_weight', '600')
        settings.button_font_size = request.POST.get('button_font_size', '0.875rem')
        settings.button_text_transform = request.POST.get('button_text_transform', 'none')
        settings.button_letter_spacing = request.POST.get('button_letter_spacing', '0.3px')
        settings.primary_bg = request.POST.get('primary_bg', global_settings.primary_color)
        settings.primary_hover_bg = request.POST.get('primary_hover_bg', global_settings.primary_hover_color)
        settings.primary_text_color = request.POST.get('primary_text_color', '#ffffff')
        settings.secondary_bg = request.POST.get('secondary_bg', '#6c757d')
        settings.secondary_hover_bg = request.POST.get('secondary_hover_bg', '#5a6268')
        settings.secondary_text_color = request.POST.get('secondary_text_color', '#ffffff')
        settings.outline_border_color = request.POST.get('outline_border_color', global_settings.primary_color)
        settings.outline_hover_bg = request.POST.get('outline_hover_bg', global_settings.primary_color)
        settings.outline_text_color = request.POST.get('outline_text_color', global_settings.primary_color)
        settings.outline_hover_text_color = request.POST.get('outline_hover_text_color', '#ffffff')
        settings.success_bg = request.POST.get('success_bg', '#28a745')
        settings.danger_bg = request.POST.get('danger_bg', '#dc3545')
        settings.warning_bg = request.POST.get('warning_bg', '#ffc107')
        settings.info_bg = request.POST.get('info_bg', '#17a2b8')
        settings.btn_lg_padding_y = request.POST.get('btn_lg_padding_y', '0.75rem')
        settings.btn_lg_padding_x = request.POST.get('btn_lg_padding_x', '2rem')
        settings.btn_lg_font_size = request.POST.get('btn_lg_font_size', '1rem')
        settings.btn_sm_padding_y = request.POST.get('btn_sm_padding_y', '0.375rem')
        settings.btn_sm_padding_x = request.POST.get('btn_sm_padding_x', '1rem')
        settings.btn_sm_font_size = request.POST.get('btn_sm_font_size', '0.8rem')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('homepage', 'Button Style Settings', '', '', request.user)
        messages.success(request, 'Button style settings updated!')
        return redirect('super_admin_button_styles')

    return render(request, 'admin/cms/design/button_settings.html', {
        'settings': settings,
        'global_settings': global_settings,
        'page_title': 'Button Styles',
    })


# ============================================================================
# CARD STYLE SETTINGS CMS
# ============================================================================

@login_required
@super_admin_required
def card_style_settings(request):
    """Card style settings (singleton)."""
    settings, _ = CardStyleSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.card_background = request.POST.get('card_background', '#ffffff')
        settings.card_border_radius = request.POST.get('card_border_radius', '12px')
        settings.card_shadow = request.POST.get('card_shadow', '0 2px 8px rgba(0,0,0,0.05)')
        settings.card_hover_shadow = request.POST.get('card_hover_shadow', '0 8px 30px rgba(0,0,0,0.12)')
        settings.card_border = request.POST.get('card_border', '1px solid #e9ecef')
        settings.card_padding = request.POST.get('card_padding', '1.5rem')
        settings.card_margin_bottom = request.POST.get('card_margin_bottom', '1.5rem')
        settings.card_header_bg = request.POST.get('card_header_bg', '#f8f9fa')
        settings.card_header_text_color = request.POST.get('card_header_text_color', '#212529')
        settings.card_header_padding = request.POST.get('card_header_padding', '1rem 1.5rem')
        settings.card_header_border = request.POST.get('card_header_border', '1px solid #e9ecef')
        settings.card_body_padding = request.POST.get('card_body_padding', '1.5rem')
        settings.section_bg_light = request.POST.get('section_bg_light', '#f8f9fa')
        settings.section_bg_dark = request.POST.get('section_bg_dark', '#0f172a')
        settings.section_padding = request.POST.get('section_padding', '4rem 0')
        settings.admin_card_border_radius = request.POST.get('admin_card_border_radius', '12px')
        settings.admin_card_shadow = request.POST.get('admin_card_shadow', '0 2px 8px rgba(0,0,0,0.05)')
        settings.admin_card_header_bg = request.POST.get('admin_card_header_bg', '#f8f9fa')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('homepage', 'Card Style Settings', '', '', request.user)
        messages.success(request, 'Card style settings updated!')
        return redirect('super_admin_card_styles')

    return render(request, 'admin/cms/design/card_settings.html', {
        'settings': settings,
        'page_title': 'Card & Section Styles',
    })


# ============================================================================
# SCROLL TO TOP SETTINGS CMS
# ============================================================================

@login_required
@super_admin_required
def scroll_to_top_settings(request):
    """Scroll-to-top button settings (singleton)."""
    settings, _ = ScrollToTopSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.is_visible = request.POST.get('is_visible') == 'on'
        settings.position_right = request.POST.get('position_right', '2rem')
        settings.position_bottom = request.POST.get('position_bottom', '2rem')
        settings.button_size = request.POST.get('button_size', 'md')
        settings.background_color = request.POST.get('background_color', '#3B7A8C')
        settings.hover_background_color = request.POST.get('hover_background_color', '#2d5f6e')
        settings.icon_color = request.POST.get('icon_color', '#ffffff')
        settings.hover_icon_color = request.POST.get('hover_icon_color', '#ffffff')
        settings.border_radius = request.POST.get('border_radius', '50%')
        settings.show_after_scroll = int(request.POST.get('show_after_scroll', 300))
        settings.scroll_duration = int(request.POST.get('scroll_duration', 500))
        settings.icon_class = request.POST.get('icon_class', 'fas fa-arrow-up')
        settings.shadow = request.POST.get('shadow', '0 4px 16px rgba(0,0,0,0.2)')
        settings.hover_shadow = request.POST.get('hover_shadow', '0 6px 24px rgba(0,0,0,0.3)')
        settings.is_active = request.POST.get('is_active') == 'on'
        settings.save()
        _log_version('homepage', 'Scroll to Top Settings', '', '', request.user)
        messages.success(request, 'Scroll-to-top button settings updated!')
        return redirect('super_admin_scroll_to_top')

    return render(request, 'admin/cms/design/scroll_to_top_settings.html', {
        'settings': settings,
        'page_title': 'Scroll to Top Button',
    })
