"""Site settings, partners, announcements and maintenance mode.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import super_admin_required
from dashboard.models import GlobalAnnouncement
from dashboard.models import MaintenanceAuditLog
from dashboard.models import MaintenanceMode
from dashboard.models import Partner
from dashboard.models import SiteSettings
from dashboard.views.shared import _log_version
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone


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
