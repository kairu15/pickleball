"""
Context processor for PickleSphere - provides global site data to all templates.
Uses Django's cache framework to reduce DB queries (~12 queries cached to ~1-2).
Cache is automatically invalidated when CMS models are saved or deleted.
"""

from django.core.cache import caches
from django.conf import settings
from .models import (ContactInfo, SiteSettings, GlobalAnnouncement, Partner,
                      HeroSectionSettings, SiteBranding, TopBarSettings,
                      NavBarSettings, NavBarMenuItem, FooterSettings,
                      FooterQuickLink, SocialPlatformSettings,
                      GlobalDesignSettings, ButtonStyleSettings,
                      CardStyleSettings, ScrollToTopSettings)


DEFAULT_CONTACT_INFO = {
    'phone': '09455470173',
    'email': 'picklesphere@gmail.com',
    'address': 'Valencia, Negros Oriental, Philippines, 6215',
    'city_country': 'Valencia, Negros Oriental, Philippines, 6215',
}

# Cache key constants — invalidated by dashboard.signals.clear_cms_cache
CMS_CACHE_PREFIX = 'cms_'
CACHE_KEYS = {
    'contact_info': f'{CMS_CACHE_PREFIX}contact_info',
    'site_settings': f'{CMS_CACHE_PREFIX}site_settings',
    'announcements': f'{CMS_CACHE_PREFIX}announcements',
    'partners': f'{CMS_CACHE_PREFIX}partners',
    'hero': f'{CMS_CACHE_PREFIX}hero',
    'branding': f'{CMS_CACHE_PREFIX}branding',
    'topbar': f'{CMS_CACHE_PREFIX}topbar',
    'navbar': f'{CMS_CACHE_PREFIX}navbar',
    'navbar_menu': f'{CMS_CACHE_PREFIX}navbar_menu',
    'footer': f'{CMS_CACHE_PREFIX}footer',
    'footer_links': f'{CMS_CACHE_PREFIX}footer_links',
    'social_platforms': f'{CMS_CACHE_PREFIX}social_platforms',
    'global_design': f'{CMS_CACHE_PREFIX}global_design',
    'button_styles': f'{CMS_CACHE_PREFIX}button_styles',
    'card_styles': f'{CMS_CACHE_PREFIX}card_styles',
    'scroll_to_top': f'{CMS_CACHE_PREFIX}scroll_to_top',
}


def _get_cache():
    """Get the CMS cache backend."""
    return caches['cms']


def _cache_get_or_set(key, fallback_fn, timeout=None):
    """
    Thread-safe cache get-or-set.
    Retrieves value from cache, or calls fallback_fn, caches result, and returns it.
    Uses the 'cms' cache namespace.
    """
    cache = _get_cache()
    result = cache.get(key)
    if result is None:
        try:
            result = fallback_fn()
            cache.set(key, result, timeout or settings.CMS_CACHE_TIMEOUT)
        except Exception:
            result = None
    return result


def _get_contact_info_cached():
    return ContactInfo.objects.first()


def _get_site_settings_cached():
    return SiteSettings.objects.first()


def _get_announcements_cached():
    return list(GlobalAnnouncement.objects.filter(is_active=True).order_by('display_order'))


def _get_partners_cached():
    return list(Partner.objects.filter(is_active=True).order_by('display_order'))


def _get_hero_cached():
    return HeroSectionSettings.objects.first()


def _get_branding_cached():
    return SiteBranding.objects.first()


def _get_topbar_cached():
    return TopBarSettings.objects.first()


def _get_navbar_cached():
    """Returns tuple (settings, menu_items_list)."""
    settings = NavBarSettings.objects.first()
    menu_items = list(NavBarMenuItem.objects.filter(is_active=True).order_by('menu_position', 'display_order'))
    return settings, menu_items


def _get_footer_cached():
    """Returns tuple (settings, quick_links_list)."""
    settings = FooterSettings.objects.first()
    quick_links = list(FooterQuickLink.objects.filter(is_active=True).order_by('display_order'))
    return settings, quick_links


def _get_social_platforms_cached():
    """Returns list of active social platform objects."""
    return list(SocialPlatformSettings.objects.filter(is_active=True).order_by('display_order'))


def _get_global_design_cached():
    return GlobalDesignSettings.objects.first()


def _get_button_styles_cached():
    return ButtonStyleSettings.objects.first()


def _get_card_styles_cached():
    return CardStyleSettings.objects.first()


def _get_scroll_to_top_cached():
    return ScrollToTopSettings.objects.first()


def site_contact_info(request):
    """
    Global context processor for all templates.
    
    All expensive DB queries are cached in the 'cms' cache namespace.
    Cache is invalidated by signals in dashboard/signals.py whenever
    any CMS model is saved or deleted.
    """
    # Fetch all data through cache (results are serialized Python objects)
    contact_info = _cache_get_or_set(CACHE_KEYS['contact_info'], _get_contact_info_cached)
    site_settings = _cache_get_or_set(CACHE_KEYS['site_settings'], _get_site_settings_cached)
    announcements = _cache_get_or_set(CACHE_KEYS['announcements'], _get_announcements_cached)
    partners = _cache_get_or_set(CACHE_KEYS['partners'], _get_partners_cached)
    hero = _cache_get_or_set(CACHE_KEYS['hero'], _get_hero_cached)
    branding = _cache_get_or_set(CACHE_KEYS['branding'], _get_branding_cached)
    topbar = _cache_get_or_set(CACHE_KEYS['topbar'], _get_topbar_cached)
    
    # Navbar and footer return tuples
    navbar_data = _cache_get_or_set(CACHE_KEYS['navbar'], _get_navbar_cached)
    navbar_settings, navbar_menu_items = navbar_data or (None, [])
    
    footer_data = _cache_get_or_set(CACHE_KEYS['footer'], _get_footer_cached)
    footer_settings, footer_quick_links = footer_data or (None, [])
    
    social_platforms = _cache_get_or_set(CACHE_KEYS['social_platforms'], _get_social_platforms_cached) or []
    global_design = _cache_get_or_set(CACHE_KEYS['global_design'], _get_global_design_cached)
    button_styles = _cache_get_or_set(CACHE_KEYS['button_styles'], _get_button_styles_cached)
    card_styles = _cache_get_or_set(CACHE_KEYS['card_styles'], _get_card_styles_cached)
    scroll_to_top_settings = _cache_get_or_set(CACHE_KEYS['scroll_to_top'], _get_scroll_to_top_cached)

    # Build contact info dict
    def ci_value(field_name):
        if not contact_info:
            return DEFAULT_CONTACT_INFO[field_name]
        return getattr(contact_info, field_name) or DEFAULT_CONTACT_INFO[field_name]

    # Filter social platforms by location (done in Python, not SQL)
    topbar_social = [p for p in social_platforms if p.show_in_topbar]
    footer_social = [p for p in social_platforms if p.show_in_footer]

    return {
        'site_contact_info': {
            'phone': ci_value('phone'),
            'email': ci_value('email'),
            'address': ci_value('address'),
            'city_country': ci_value('city_country'),
        },
        'site_settings': site_settings,
        'global_announcements': announcements,
        'partners': partners,
        # CMS content
        'hero_settings': hero,
        'site_branding': branding,
        'topbar_settings': topbar,
        'navbar_settings': navbar_settings,
        'navbar_menu_items': navbar_menu_items,
        'footer_settings': footer_settings,
        'footer_quick_links': footer_quick_links,
        'social_platforms': social_platforms,
        'topbar_social_platforms': topbar_social,
        'footer_social_platforms': footer_social,
        # Website Design settings
        'global_design_settings': global_design,
        'button_style_settings': button_styles,
        'card_style_settings': card_styles,
        'scroll_to_top_settings': scroll_to_top_settings,
    }
