"""
Signal handlers for CMS cache invalidation.
Whenever a CMS model is saved or deleted, the entire 'cms' cache namespace
is cleared so the context processor fetches fresh data on the next request.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .cache_utils import invalidate_all_caches

# List of all CMS model classes that should trigger cache invalidation
CMS_MODELS = []


def _collect_cms_models():
    """Lazy-import CMS models to avoid AppRegistryNotReady at import time."""
    global CMS_MODELS
    if not CMS_MODELS:
        from .models import (
            ContactInfo, SiteSettings, GlobalAnnouncement, Partner,
            HeroSectionSettings, SiteBranding, TopBarSettings,
            NavBarSettings, NavBarMenuItem, FooterSettings,
            FooterQuickLink, SocialPlatformSettings,
            GlobalDesignSettings, ButtonStyleSettings,
            CardStyleSettings, ScrollToTopSettings,
        )
        CMS_MODELS = [
            ContactInfo, SiteSettings, GlobalAnnouncement, Partner,
            HeroSectionSettings, SiteBranding, TopBarSettings,
            NavBarSettings, NavBarMenuItem, FooterSettings,
            FooterQuickLink, SocialPlatformSettings,
            GlobalDesignSettings, ButtonStyleSettings,
            CardStyleSettings, ScrollToTopSettings,
        ]
    return CMS_MODELS


def clear_cms_cache(sender, **kwargs):
    """Clear CMS, page and fragment caches. Used as post_save/post_delete handler.
    Delegates to cache_utils.invalidate_all_caches so every namespace tied to
    public content is refreshed together."""
    invalidate_all_caches(sender, **kwargs)


def connect_signals():
    """Connect cache-clear signals to all CMS models.
    Called explicitly from DashboardConfig.ready() to ensure
    Django's app registry is fully loaded."""
    models = _collect_cms_models()
    for model in models:
        post_save.connect(clear_cms_cache, sender=model, weak=False)
        post_delete.connect(clear_cms_cache, sender=model, weak=False)
