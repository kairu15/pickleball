"""Branding, top bar, navbar, footer and social media CMS.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import super_admin_required
from dashboard.models import FooterQuickLink
from dashboard.models import FooterSettings
from dashboard.models import NavBarMenuItem
from dashboard.models import NavBarSettings
from dashboard.models import SiteBranding
from dashboard.models import SocialPlatformSettings
from dashboard.models import TopBarSettings
from dashboard.views.shared import _log_version
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render


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
