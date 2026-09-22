"""Feature-grouped dashboard views (split out of the former monolithic
``dashboard.views`` and ``dashboard.cms_views`` modules).

Every previously public view callable is re-exported here so that
``from dashboard.views import <name>``, ``from . import views`` plus
``views.<name>`` in the URL modules, and ``dashboard.cms_views.<name>``
all keep resolving exactly as before.

Shared constants/helpers live in :mod:`dashboard.views.shared` and are
imported directly by the feature modules (never through this package
``__init__``) so no import cycle can form.
"""

# --- home ---
from dashboard.views.home import (
    home_view, dashboard_view, staff_dashboard_view,
)

# --- public_pages ---
from dashboard.views.public_pages import (
    all_courts_view, court_view_view, pricing_view, about_view,
    contact_view, privacy_policy_view, terms_of_service_view, faq_view,
)

# --- users ---
from dashboard.views.users import (
    user_dashboard_view, user_messages_view, submit_rating_view,
    check_pending_rating_view,
)

# --- analytics ---
from dashboard.views.analytics import (
    admin_dashboard_view, dashboard_export_view, cache_monitor_view,
    rating_list_view,
)

# --- admin_panel ---
from dashboard.views.admin_panel import (
    contact_messages_view, contact_message_detail_view,
    admin_reject_testimonial_view,
)

# --- cms_homepage ---
from dashboard.views.cms_homepage import (
    homepage_management, homepage_edit_content, populate_homepage_content,
    toggle_featured_rating, homepage_edit_testimonial,
    homepage_edit_amenity, homepage_edit_gallery,
    homepage_delete_testimonial, homepage_delete_amenity,
    homepage_delete_gallery,
)

# --- cms_pricing ---
from dashboard.views.cms_pricing import (
    pricing_management, pricing_edit_content, pricing_delete_content,
    pricing_edit_tier, pricing_delete_tier, pricing_edit_faq,
    pricing_delete_faq,
)

# --- cms_about ---
from dashboard.views.cms_about import (
    about_management, about_edit_content, about_delete_content,
    about_edit_milestone, about_delete_milestone, about_edit_team_member,
    about_delete_team_member, about_edit_facility, about_delete_facility,
    about_edit_why_item, about_delete_why_item, about_add_gallery_image,
    about_delete_gallery_image,
)

# --- cms_contact ---
from dashboard.views.cms_contact import (
    contact_management, contact_edit_content, contact_delete_content,
    contact_edit_info, contact_edit_business_hour,
    contact_delete_business_hour, contact_edit_faq, contact_delete_faq,
    contact_edit_social_link, contact_delete_social_link,
)

# --- cms_pages ---
from dashboard.views.cms_pages import (
    courts_page_settings, courts_featured_add, courts_featured_edit,
    courts_featured_delete, tournaments_page_settings,
    tournament_category_add, tournament_category_edit,
    tournament_category_delete, tournament_featured_add,
    tournament_featured_edit, tournament_featured_delete,
    tournament_announcement_add, tournament_announcement_edit,
    tournament_announcement_delete, equipment_page_settings,
    equipment_category_add, equipment_category_edit,
    equipment_category_delete, equipment_featured_add,
    equipment_featured_edit, equipment_featured_delete,
)

# --- cms_content ---
from dashboard.views.cms_content import (
    content_version_list, faq_cms_settings, faq_category_add,
    faq_category_edit, faq_category_delete, faq_item_add, faq_item_edit,
    faq_item_delete, terms_cms_settings, terms_section_add,
    terms_section_edit, terms_section_delete, privacy_cms_settings,
    privacy_section_add, privacy_section_edit, privacy_section_delete,
    media_library_view, media_library_upload, media_library_edit,
    media_library_delete, hero_section_settings, hero_section_preview,
)

# --- cms_navigation ---
from dashboard.views.cms_navigation import (
    site_branding_settings, site_branding_remove_logo,
    site_branding_restore_defaults, topbar_settings, navbar_settings,
    navbar_menu_item_add, navbar_menu_item_edit, navbar_menu_item_delete,
    footer_settings, footer_quick_link_add, footer_quick_link_edit,
    footer_quick_link_delete, social_media_settings, social_platform_edit,
)

# --- site_settings ---
from dashboard.views.site_settings import (
    maintenance_mode_settings, site_settings_view, partner_add,
    partner_edit, partner_delete, announcement_add, announcement_edit,
    announcement_delete,
)

# --- design ---
from dashboard.views.design import (
    global_design_settings, button_style_settings, card_style_settings,
    scroll_to_top_settings,
)

__all__ = [
    about_add_gallery_image, about_delete_content, about_delete_facility,
    about_delete_gallery_image, about_delete_milestone,
    about_delete_team_member, about_delete_why_item, about_edit_content,
    about_edit_facility, about_edit_milestone, about_edit_team_member,
    about_edit_why_item, about_management, about_view,
    admin_dashboard_view, admin_reject_testimonial_view, all_courts_view,
    announcement_add, announcement_delete, announcement_edit,
    button_style_settings, cache_monitor_view, card_style_settings,
    check_pending_rating_view, contact_delete_business_hour,
    contact_delete_content, contact_delete_faq, contact_delete_social_link,
    contact_edit_business_hour, contact_edit_content, contact_edit_faq,
    contact_edit_info, contact_edit_social_link, contact_management,
    contact_message_detail_view, contact_messages_view, contact_view,
    content_version_list, court_view_view, courts_featured_add,
    courts_featured_delete, courts_featured_edit, courts_page_settings,
    dashboard_export_view, dashboard_view, equipment_category_add,
    equipment_category_delete, equipment_category_edit,
    equipment_featured_add, equipment_featured_delete,
    equipment_featured_edit, equipment_page_settings, faq_category_add,
    faq_category_delete, faq_category_edit, faq_cms_settings, faq_item_add,
    faq_item_delete, faq_item_edit, faq_view, footer_quick_link_add,
    footer_quick_link_delete, footer_quick_link_edit, footer_settings,
    global_design_settings, hero_section_preview, hero_section_settings,
    home_view, homepage_delete_amenity, homepage_delete_gallery,
    homepage_delete_testimonial, homepage_edit_amenity,
    homepage_edit_content, homepage_edit_gallery,
    homepage_edit_testimonial, homepage_management,
    maintenance_mode_settings, media_library_delete, media_library_edit,
    media_library_upload, media_library_view, navbar_menu_item_add,
    navbar_menu_item_delete, navbar_menu_item_edit, navbar_settings,
    partner_add, partner_delete, partner_edit, populate_homepage_content,
    pricing_delete_content, pricing_delete_faq, pricing_delete_tier,
    pricing_edit_content, pricing_edit_faq, pricing_edit_tier,
    pricing_management, pricing_view, privacy_cms_settings,
    privacy_policy_view, privacy_section_add, privacy_section_delete,
    privacy_section_edit, rating_list_view, scroll_to_top_settings,
    site_branding_remove_logo, site_branding_restore_defaults,
    site_branding_settings, site_settings_view, social_media_settings,
    social_platform_edit, staff_dashboard_view, submit_rating_view,
    terms_cms_settings, terms_of_service_view, terms_section_add,
    terms_section_delete, terms_section_edit, toggle_featured_rating,
    topbar_settings, tournament_announcement_add,
    tournament_announcement_delete, tournament_announcement_edit,
    tournament_category_add, tournament_category_delete,
    tournament_category_edit, tournament_featured_add,
    tournament_featured_delete, tournament_featured_edit,
    tournaments_page_settings, user_dashboard_view, user_messages_view,
]
