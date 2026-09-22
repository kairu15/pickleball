"""
Signal wiring for automatic cache invalidation across the public site.

Every model whose data appears on cached pages (CMS content, courts,
equipment, tournaments, reservations) is connected to
``invalidate_all_caches`` so that any create/update/delete automatically
refreshes cached pages, page data and template fragments.
"""

from django.db.models.signals import post_save, post_delete

from .cache_utils import invalidate_all_caches

# Lazy-loaded after the app registry is ready (see connect_cache_signals)
PAGE_CACHE_MODELS = []


def _collect_models():
    """Lazy-import content models across apps to avoid AppRegistryNotReady."""
    global PAGE_CACHE_MODELS
    if PAGE_CACHE_MODELS:
        return PAGE_CACHE_MODELS

    from dashboard.models import (
        PricingContent, PricingTier, PricingFAQ,
        AboutContent, Milestone, TeamMember, Facility, WhyChooseItem,
        ContactContent, ContactInfo, BusinessHour, ContactFAQ, SocialLink,
        Testimonial, Rating, Amenity, GalleryImage, HomePageContent,
        AboutGalleryImage,        CourtPageSettings, FeaturedCourt,
        TournamentPageSettings, TournamentCategory, FeaturedTournament,
        TournamentAnnouncement, EquipmentPageSettings, EquipmentCategory,
        FeaturedEquipment, FAQPageContent, FAQCategory, FAQItem,
        TermsContent, TermsSection, PrivacyContent, PrivacySection,
        SiteSettings, Partner, GlobalAnnouncement,
        HeroSectionSettings, SiteBranding, TopBarSettings,
        NavBarSettings, NavBarMenuItem, FooterSettings, FooterQuickLink,
        SocialPlatformSettings, GlobalDesignSettings, ButtonStyleSettings,
        CardStyleSettings, ScrollToTopSettings,
    )
    from courts.models import Court, Site, CourtImage, CourtAvailability
    from equipment.models import Equipment
    from tournaments.models import Tournament, Registration
    from reservations.models import Reservation

    PAGE_CACHE_MODELS = [
        # ---- CMS / public page content (dashboard app) ----
        PricingContent, PricingTier, PricingFAQ,
        AboutContent, Milestone, TeamMember, Facility, WhyChooseItem,
        ContactContent, ContactInfo, BusinessHour, ContactFAQ, SocialLink,
        Testimonial, Rating, Amenity, GalleryImage, HomePageContent,
        AboutGalleryImage,        CourtPageSettings, FeaturedCourt,
        TournamentPageSettings, TournamentCategory, FeaturedTournament,
        TournamentAnnouncement, EquipmentPageSettings, EquipmentCategory,
        FeaturedEquipment, FAQPageContent, FAQCategory, FAQItem,
        TermsContent, TermsSection, PrivacyContent, PrivacySection,
        SiteSettings, Partner, GlobalAnnouncement,
        HeroSectionSettings, SiteBranding, TopBarSettings,
        NavBarSettings, NavBarMenuItem, FooterSettings, FooterQuickLink,
        SocialPlatformSettings, GlobalDesignSettings, ButtonStyleSettings,
        CardStyleSettings, ScrollToTopSettings,
        # ---- Courts ----
        Court, Site, CourtImage, CourtAvailability,
        # ---- Equipment ----
        Equipment,
        # ---- Tournaments ----
        Tournament, Registration,
        # ---- Reservations (court availability / list pages) ----
        Reservation,
    ]
    return PAGE_CACHE_MODELS


def connect_cache_signals():
    """Connect invalidation signals. Called from DashboardConfig.ready()."""
    for model in _collect_models():
        post_save.connect(invalidate_all_caches, sender=model, weak=False)
        post_delete.connect(invalidate_all_caches, sender=model, weak=False)
