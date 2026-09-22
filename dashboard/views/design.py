"""Global design system: design tokens, buttons, cards, scroll-to-top.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import super_admin_required
from dashboard.models import ButtonStyleSettings
from dashboard.models import CardStyleSettings
from dashboard.models import GlobalDesignSettings
from dashboard.models import ScrollToTopSettings
from dashboard.views.shared import _log_version
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render


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
