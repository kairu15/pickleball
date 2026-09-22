from django.urls import path
from django.urls import path
from . import views
from . import cms_views
from accounts import views as accounts_views

urlpatterns = [
    # Profile
    path('profile/', accounts_views.profile_view, name='super_admin_profile'),

    # Analytics Dashboard
    path('analytics/', views.admin_dashboard_view, name='super_admin_analytics'),
    path('analytics/export/', views.dashboard_export_view, name='super_admin_analytics_export'),
    path('ratings/', views.rating_list_view, name='super_admin_rating_list'),

    # Cache Monitor
    path('cache-monitor/', views.cache_monitor_view, name='super_admin_cache_monitor'),

    # Homepage Content Management
    path('homepage/', views.homepage_management, name='super_admin_homepage'),
    path('homepage/content/<int:content_id>/edit/', views.homepage_edit_content, name='super_admin_homepage_content_edit'),
    path('homepage/populate/', views.populate_homepage_content, name='super_admin_homepage_populate'),
    path('homepage/amenity/add/', views.homepage_edit_amenity, name='super_admin_homepage_amenity_add'),
    path('homepage/amenity/<int:amenity_id>/edit/', views.homepage_edit_amenity, name='super_admin_homepage_amenity_edit'),
    path('homepage/amenity/<int:amenity_id>/delete/', views.homepage_delete_amenity, name='super_admin_homepage_amenity_delete'),
    path('homepage/gallery/add/', views.homepage_edit_gallery, name='super_admin_homepage_gallery_add'),
    path('homepage/gallery/<int:gallery_id>/edit/', views.homepage_edit_gallery, name='super_admin_homepage_gallery_edit'),
    path('homepage/gallery/<int:gallery_id>/delete/', views.homepage_delete_gallery, name='super_admin_homepage_gallery_delete'),
    path('homepage/ratings/<int:rating_id>/toggle-featured/', views.toggle_featured_rating, name='super_admin_toggle_featured_rating'),

    # Pricing Page Management
    path('pricing/', views.pricing_management, name='super_admin_pricing'),
    path('pricing/content/add/', views.pricing_edit_content, name='super_admin_pricing_content_add'),
    path('pricing/content/<int:content_id>/edit/', views.pricing_edit_content, name='super_admin_pricing_content_edit'),
    path('pricing/content/<int:content_id>/delete/', views.pricing_delete_content, name='super_admin_pricing_content_delete'),
    path('pricing/tier/add/', views.pricing_edit_tier, name='super_admin_pricing_tier_add'),
    path('pricing/tier/<int:tier_id>/edit/', views.pricing_edit_tier, name='super_admin_pricing_tier_edit'),
    path('pricing/tier/<int:tier_id>/delete/', views.pricing_delete_tier, name='super_admin_pricing_tier_delete'),
    path('pricing/faq/add/', views.pricing_edit_faq, name='super_admin_pricing_faq_add'),
    path('pricing/faq/<int:faq_id>/edit/', views.pricing_edit_faq, name='super_admin_pricing_faq_edit'),
    path('pricing/faq/<int:faq_id>/delete/', views.pricing_delete_faq, name='super_admin_pricing_faq_delete'),

    # About Page Management
    path('about/', views.about_management, name='super_admin_about'),
    path('about/content/add/', views.about_edit_content, name='super_admin_about_content_add'),
    path('about/content/<int:content_id>/edit/', views.about_edit_content, name='super_admin_about_content_edit'),
    path('about/content/<int:content_id>/delete/', views.about_delete_content, name='super_admin_about_content_delete'),
    path('about/milestone/add/', views.about_edit_milestone, name='super_admin_about_milestone_add'),
    path('about/milestone/<int:milestone_id>/edit/', views.about_edit_milestone, name='super_admin_about_milestone_edit'),
    path('about/milestone/<int:milestone_id>/delete/', views.about_delete_milestone, name='super_admin_about_milestone_delete'),
    path('about/team/add/', views.about_edit_team_member, name='super_admin_about_team_add'),
    path('about/team/<int:member_id>/edit/', views.about_edit_team_member, name='super_admin_about_team_edit'),
    path('about/team/<int:member_id>/delete/', views.about_delete_team_member, name='super_admin_about_team_delete'),
    path('about/facility/add/', views.about_edit_facility, name='super_admin_about_facility_add'),
    path('about/facility/<int:facility_id>/edit/', views.about_edit_facility, name='super_admin_about_facility_edit'),
    path('about/facility/<int:facility_id>/delete/', views.about_delete_facility, name='super_admin_about_facility_delete'),
    path('about/why-item/add/', views.about_edit_why_item, name='super_admin_about_why_add'),
    path('about/why-item/<int:item_id>/edit/', views.about_edit_why_item, name='super_admin_about_why_edit'),
    path('about/why-item/<int:item_id>/delete/', views.about_delete_why_item, name='super_admin_about_why_delete'),
    path('about/gallery/add/', views.about_add_gallery_image, name='super_admin_about_gallery_add'),
    path('about/gallery/<int:image_id>/delete/', views.about_delete_gallery_image, name='super_admin_about_gallery_delete'),

    # Contact Page Management
    path('contact/', views.contact_management, name='super_admin_contact'),
    path('contact/content/add/', views.contact_edit_content, name='super_admin_contact_content_add'),
    path('contact/content/<int:content_id>/edit/', views.contact_edit_content, name='super_admin_contact_content_edit'),
    path('contact/content/<int:content_id>/delete/', views.contact_delete_content, name='super_admin_contact_content_delete'),
    path('contact/info/edit/', views.contact_edit_info, name='super_admin_contact_info'),
    path('contact/hour/add/', views.contact_edit_business_hour, name='super_admin_contact_hour_add'),
    path('contact/hour/<int:hour_id>/edit/', views.contact_edit_business_hour, name='super_admin_contact_hour_edit'),
    path('contact/hour/<int:hour_id>/delete/', views.contact_delete_business_hour, name='super_admin_contact_hour_delete'),
    path('contact/faq/add/', views.contact_edit_faq, name='super_admin_contact_faq_add'),
    path('contact/faq/<int:faq_id>/edit/', views.contact_edit_faq, name='super_admin_contact_faq_edit'),
    path('contact/faq/<int:faq_id>/delete/', views.contact_delete_faq, name='super_admin_contact_faq_delete'),
    path('contact/social/add/', views.contact_edit_social_link, name='super_admin_contact_social_add'),
    path('contact/social/<int:link_id>/edit/', views.contact_edit_social_link, name='super_admin_contact_social_edit'),
    path('contact/social/<int:link_id>/delete/', views.contact_delete_social_link, name='super_admin_contact_social_delete'),
    path('contact/messages/', views.contact_messages_view, name='super_admin_contact_messages'),
    path('contact/messages/<int:message_id>/', views.contact_message_detail_view, name='super_admin_contact_message_detail'),

    # ========== COURTS PAGE CMS ==========
    path('cms/courts/', cms_views.courts_page_settings, name='super_admin_courts_cms'),
    path('cms/courts/featured/add/', cms_views.courts_featured_add, name='super_admin_courts_featured_add'),
    path('cms/courts/featured/<int:featured_id>/edit/', cms_views.courts_featured_edit, name='super_admin_courts_featured_edit'),
    path('cms/courts/featured/<int:featured_id>/delete/', cms_views.courts_featured_delete, name='super_admin_courts_featured_delete'),

    # ========== TOURNAMENTS PAGE CMS ==========
    path('cms/tournaments/', cms_views.tournaments_page_settings, name='super_admin_tournaments_cms'),
    path('cms/tournaments/category/add/', cms_views.tournament_category_add, name='super_admin_tournament_category_add'),
    path('cms/tournaments/category/<int:cat_id>/edit/', cms_views.tournament_category_edit, name='super_admin_tournament_category_edit'),
    path('cms/tournaments/category/<int:cat_id>/delete/', cms_views.tournament_category_delete, name='super_admin_tournament_category_delete'),
    path('cms/tournaments/featured/add/', cms_views.tournament_featured_add, name='super_admin_tournament_featured_add'),
    path('cms/tournaments/featured/<int:featured_id>/edit/', cms_views.tournament_featured_edit, name='super_admin_tournament_featured_edit'),
    path('cms/tournaments/featured/<int:featured_id>/delete/', cms_views.tournament_featured_delete, name='super_admin_tournament_featured_delete'),
    path('cms/tournaments/announcement/add/', cms_views.tournament_announcement_add, name='super_admin_tournament_announcement_add'),
    path('cms/tournaments/announcement/<int:ann_id>/edit/', cms_views.tournament_announcement_edit, name='super_admin_tournament_announcement_edit'),
    path('cms/tournaments/announcement/<int:ann_id>/delete/', cms_views.tournament_announcement_delete, name='super_admin_tournament_announcement_delete'),

    # ========== EQUIPMENT PAGE CMS ==========
    path('cms/equipment/', cms_views.equipment_page_settings, name='super_admin_equipment_cms'),
    path('cms/equipment/category/add/', cms_views.equipment_category_add, name='super_admin_equipment_category_add'),
    path('cms/equipment/category/<int:cat_id>/edit/', cms_views.equipment_category_edit, name='super_admin_equipment_category_edit'),
    path('cms/equipment/category/<int:cat_id>/delete/', cms_views.equipment_category_delete, name='super_admin_equipment_category_delete'),
    path('cms/equipment/featured/add/', cms_views.equipment_featured_add, name='super_admin_equipment_featured_add'),
    path('cms/equipment/featured/<int:featured_id>/edit/', cms_views.equipment_featured_edit, name='super_admin_equipment_featured_edit'),
    path('cms/equipment/featured/<int:featured_id>/delete/', cms_views.equipment_featured_delete, name='super_admin_equipment_featured_delete'),

    # ========== MAINTENANCE MODE ==========
    path('maintenance/', cms_views.maintenance_mode_settings, name='super_admin_maintenance'),

    # ========== FAQ PAGE CMS ==========
    path('cms/faq/', cms_views.faq_cms_settings, name='super_admin_faq_cms'),
    path('cms/faq/category/add/', cms_views.faq_category_add, name='super_admin_faq_category_add'),
    path('cms/faq/category/<int:cat_id>/edit/', cms_views.faq_category_edit, name='super_admin_faq_category_edit'),
    path('cms/faq/category/<int:cat_id>/delete/', cms_views.faq_category_delete, name='super_admin_faq_category_delete'),
    path('cms/faq/item/add/', cms_views.faq_item_add, name='super_admin_faq_item_add'),
    path('cms/faq/item/<int:item_id>/edit/', cms_views.faq_item_edit, name='super_admin_faq_item_edit'),
    path('cms/faq/item/<int:item_id>/delete/', cms_views.faq_item_delete, name='super_admin_faq_item_delete'),

    # ========== TERMS OF SERVICE CMS ==========
    path('cms/terms/', cms_views.terms_cms_settings, name='super_admin_terms_cms'),
    path('cms/terms/section/add/', cms_views.terms_section_add, name='super_admin_terms_section_add'),
    path('cms/terms/section/<int:section_id>/edit/', cms_views.terms_section_edit, name='super_admin_terms_section_edit'),
    path('cms/terms/section/<int:section_id>/delete/', cms_views.terms_section_delete, name='super_admin_terms_section_delete'),

    # ========== PRIVACY POLICY CMS ==========
    path('cms/privacy/', cms_views.privacy_cms_settings, name='super_admin_privacy_cms'),
    path('cms/privacy/section/add/', cms_views.privacy_section_add, name='super_admin_privacy_section_add'),
    path('cms/privacy/section/<int:section_id>/edit/', cms_views.privacy_section_edit, name='super_admin_privacy_section_edit'),
    path('cms/privacy/section/<int:section_id>/delete/', cms_views.privacy_section_delete, name='super_admin_privacy_section_delete'),

    # ========== MEDIA LIBRARY ==========
    path('media/', cms_views.media_library_view, name='super_admin_media_library'),
    path('media/upload/', cms_views.media_library_upload, name='super_admin_media_upload'),
    path('media/<int:media_id>/edit/', cms_views.media_library_edit, name='super_admin_media_edit'),
    path('media/<int:media_id>/delete/', cms_views.media_library_delete, name='super_admin_media_delete'),

    # ========== SITE SETTINGS ==========
    path('site-settings/', cms_views.site_settings_view, name='super_admin_site_settings'),
    path('site-settings/partner/add/', cms_views.partner_add, name='super_admin_partner_add'),
    path('site-settings/partner/<int:partner_id>/edit/', cms_views.partner_edit, name='super_admin_partner_edit'),
    path('site-settings/partner/<int:partner_id>/delete/', cms_views.partner_delete, name='super_admin_partner_delete'),
    path('site-settings/announcement/add/', cms_views.announcement_add, name='super_admin_announcement_add'),
    path('site-settings/announcement/<int:ann_id>/edit/', cms_views.announcement_edit, name='super_admin_announcement_edit'),
    path('site-settings/announcement/<int:ann_id>/delete/', cms_views.announcement_delete, name='super_admin_announcement_delete'),

    # ========== HERO SECTION CMS ==========
    path('cms/hero/', cms_views.hero_section_settings, name='super_admin_hero_cms'),
    path('cms/hero/preview/', cms_views.hero_section_preview, name='super_admin_hero_preview'),

    # ========== WEBSITE BRANDING CMS ==========
    path('cms/branding/', cms_views.site_branding_settings, name='super_admin_branding_cms'),
    path('cms/branding/logo/<str:logo_field>/remove/', cms_views.site_branding_remove_logo, name='super_admin_branding_remove_logo'),
    path('cms/branding/restore-defaults/', cms_views.site_branding_restore_defaults, name='super_admin_branding_restore'),

    # ========== TOP BAR CMS ==========
    path('cms/topbar/', cms_views.topbar_settings, name='super_admin_topbar_cms'),

    # ========== NAVIGATION BAR CMS ==========
    path('cms/navbar/', cms_views.navbar_settings, name='super_admin_navbar_cms'),
    path('cms/navbar/menu/add/', cms_views.navbar_menu_item_add, name='super_admin_navbar_menu_add'),
    path('cms/navbar/menu/<int:item_id>/edit/', cms_views.navbar_menu_item_edit, name='super_admin_navbar_menu_edit'),
    path('cms/navbar/menu/<int:item_id>/delete/', cms_views.navbar_menu_item_delete, name='super_admin_navbar_menu_delete'),

    # ========== FOOTER CMS ==========
    path('cms/footer/', cms_views.footer_settings, name='super_admin_footer_cms'),
    path('cms/footer/quick-link/add/', cms_views.footer_quick_link_add, name='super_admin_footer_quick_link_add'),
    path('cms/footer/quick-link/<int:link_id>/edit/', cms_views.footer_quick_link_edit, name='super_admin_footer_quick_link_edit'),
    path('cms/footer/quick-link/<int:link_id>/delete/', cms_views.footer_quick_link_delete, name='super_admin_footer_quick_link_delete'),

    # ========== SOCIAL MEDIA CMS ==========
    path('cms/social/', cms_views.social_media_settings, name='super_admin_social_cms'),
    path('cms/social/<int:platform_id>/edit/', cms_views.social_platform_edit, name='super_admin_social_platform_edit'),

    # ========== GLOBAL DESIGN SYSTEM CMS ==========
    path('cms/design/global/', cms_views.global_design_settings, name='super_admin_global_design'),

    # ========== BUTTON STYLES CMS ==========
    path('cms/design/buttons/', cms_views.button_style_settings, name='super_admin_button_styles'),

    # ========== CARD STYLES CMS ==========
    path('cms/design/cards/', cms_views.card_style_settings, name='super_admin_card_styles'),

    # ========== SCROLL TO TOP CMS ==========
    path('cms/design/scroll-to-top/', cms_views.scroll_to_top_settings, name='super_admin_scroll_to_top'),

    # ========== CONTENT VERSION HISTORY ==========
    path('versions/', cms_views.content_version_list, name='super_admin_content_versions'),
]
