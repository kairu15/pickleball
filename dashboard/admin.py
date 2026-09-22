from django.contrib import admin
from .models import (
    Testimonial, Rating, Amenity, GalleryImage, HomePageContent,
    PricingContent, PricingTier, PricingFAQ,
    AboutContent, Milestone, TeamMember, Facility, WhyChooseItem,
    ContactContent, ContactInfo, BusinessHour, ContactFAQ, SocialLink,
    # CMS Models
    CourtPageSettings, FeaturedCourt,
    TournamentPageSettings, TournamentCategory, FeaturedTournament, TournamentAnnouncement,
    EquipmentPageSettings, EquipmentCategory, FeaturedEquipment,
    MaintenanceMode, MaintenanceAuditLog,
    SiteSettings, Partner, GlobalAnnouncement,
    ContentVersion,
    # NEW CMS Models
    HeroSectionSettings, SiteBranding,
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


# Pricing Admin Classes
@admin.register(PricingContent)
class PricingContentAdmin(admin.ModelAdmin):
    list_display = ['section', 'content_short', 'is_active', 'updated_at']
    list_filter = ['is_active', 'section']
    search_fields = ['section', 'content']
    list_editable = ['is_active']
    fields = ['section', 'content', 'is_active']
    readonly_fields = ['updated_at']

    def content_short(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_short.short_description = 'Content Preview'


@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'period', 'is_recommended', 'is_active', 'display_order']
    list_filter = ['is_active', 'is_recommended']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'price']
    list_editable = ['is_active', 'is_recommended', 'display_order', 'price']
    fields = ['name', 'price', 'period', 'description', 'features', 'is_recommended', 'is_active', 'display_order']


@admin.register(PricingFAQ)
class PricingFAQAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['question', 'answer']
    ordering = ['display_order', '-created_at']
    list_editable = ['is_active', 'display_order']
    fields = ['question', 'answer', 'is_active', 'display_order']

    def question_short(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_short.short_description = 'Question'


# About Admin Classes
@admin.register(AboutContent)
class AboutContentAdmin(admin.ModelAdmin):
    list_display = ['section', 'content_short', 'is_active', 'updated_at']
    list_filter = ['is_active', 'section']
    search_fields = ['section', 'content']
    list_editable = ['is_active']
    fields = ['section', 'content', 'is_active']
    readonly_fields = ['updated_at']

    def content_short(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_short.short_description = 'Content Preview'


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['year', 'title', 'color', 'is_active', 'display_order']
    list_filter = ['is_active', 'color']
    search_fields = ['year', 'title', 'description']
    ordering = ['display_order', 'year']
    list_editable = ['is_active', 'color', 'display_order']
    fields = ['year', 'title', 'description', 'color', 'is_active', 'display_order']


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'color', 'is_active', 'display_order', 'photo_preview']
    list_filter = ['is_active', 'color']
    search_fields = ['name', 'role', 'bio']
    ordering = ['display_order', 'name']
    list_editable = ['is_active', 'display_order']
    fields = ['name', 'role', 'bio', 'photo', 'linkedin_url', 'twitter_url', 'color', 'is_active', 'display_order']

    def photo_preview(self, obj):
        if obj.photo:
            return f'<img src="{obj.photo.url}" style="max-height: 50px; max-width: 50px; border-radius: 50%;" />'
        return '<div style="width: 50px; height: 50px; background: #ddd; border-radius: 50%; display: flex; align-items: center; justify-content: center;"><i class="fas fa-user"></i></div>'
    photo_preview.allow_tags = True
    photo_preview.short_description = 'Photo'


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['title', 'icon', 'color', 'is_active', 'display_order']
    list_filter = ['is_active', 'color']
    search_fields = ['title', 'description']
    ordering = ['display_order', 'title']
    list_editable = ['is_active', 'icon', 'color', 'display_order']
    fields = ['icon', 'title', 'description', 'color', 'is_active', 'display_order']


@admin.register(WhyChooseItem)
class WhyChooseItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'icon', 'color', 'is_active', 'display_order']
    list_filter = ['is_active', 'color']
    search_fields = ['title', 'description']
    ordering = ['display_order', 'title']
    list_editable = ['is_active', 'icon', 'color', 'display_order']
    fields = ['icon', 'title', 'description', 'color', 'is_active', 'display_order']


# Contact Admin Classes
@admin.register(ContactContent)
class ContactContentAdmin(admin.ModelAdmin):
    list_display = ['section', 'content_short', 'is_active', 'updated_at']
    list_filter = ['is_active', 'section']
    search_fields = ['section', 'content']
    list_editable = ['is_active']
    fields = ['section', 'content', 'is_active']
    readonly_fields = ['updated_at']

    def content_short(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_short.short_description = 'Content Preview'


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ['phone', 'email', 'address_short', 'updated_at']
    fields = ['phone', 'email', 'address', 'city_country', 'google_maps_url']
    readonly_fields = ['updated_at']

    def address_short(self, obj):
        return obj.address[:50] + '...' if len(obj.address) > 50 else obj.address
    address_short.short_description = 'Address'

    def has_add_permission(self, request):
        # Only allow one instance
        return not ContactInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BusinessHour)
class BusinessHourAdmin(admin.ModelAdmin):
    list_display = ['day_range', 'hours', 'icon_color', 'is_active', 'display_order']
    list_filter = ['is_active', 'icon_color']
    ordering = ['display_order']
    list_editable = ['is_active', 'icon_color', 'hours', 'display_order']
    fields = ['day_range', 'hours', 'icon_color', 'is_active', 'display_order']


@admin.register(ContactFAQ)
class ContactFAQAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'icon_color', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'icon_color', 'created_at']
    search_fields = ['question', 'answer']
    ordering = ['display_order', '-created_at']
    list_editable = ['is_active', 'icon_color', 'display_order']
    fields = ['question', 'answer', 'icon_color', 'is_active', 'display_order']

    def question_short(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_short.short_description = 'Question'


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ['platform', 'url_short', 'is_active', 'display_order']
    list_filter = ['is_active', 'platform']
    ordering = ['display_order', 'platform']
    list_editable = ['is_active', 'display_order']
    fields = ['platform', 'url', 'is_active', 'display_order']

    def url_short(self, obj):
        return obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
    url_short.short_description = 'URL'


# Homepage Admin Classes (existing)
@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'reservation', 'rating', 'comment_short', 'is_featured', 'created_at']
    list_filter = ['is_featured', 'rating', 'created_at']
    list_editable = ['is_featured']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'comment']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    fields = ['user', 'reservation', 'rating', 'comment', 'is_featured', 'created_at', 'updated_at']

    def comment_short(self, obj):
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return '-'
    comment_short.short_description = 'Comment'


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'rating', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'rating', 'created_at']
    search_fields = ['name', 'role', 'text']
    ordering = ['display_order', '-created_at']
    list_editable = ['is_active', 'display_order', 'rating']
    fields = ['name', 'role', 'rating', 'text', 'avatar', 'is_active', 'display_order']


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['title', 'icon', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['display_order', 'title']
    list_editable = ['is_active', 'display_order']
    fields = ['icon', 'title', 'description', 'is_active', 'display_order']


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'alt_text', 'is_active', 'display_order', 'created_at', 'image_preview']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'alt_text']
    ordering = ['display_order', '-created_at']
    list_editable = ['is_active', 'display_order', 'title', 'alt_text']
    fields = ['image', 'title', 'alt_text', 'is_active', 'display_order']

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 50px; max-width: 100px;" />'
        return 'No image'
    image_preview.allow_tags = True
    image_preview.short_description = 'Preview'


@admin.register(HomePageContent)
class HomePageContentAdmin(admin.ModelAdmin):
    list_display = ['section', 'is_active', 'updated_at']
    list_filter = ['is_active', 'section']
    search_fields = ['section', 'content']
    list_editable = ['is_active']
    fields = ['section', 'content', 'is_active']
    readonly_fields = ['updated_at']


# ============================================================================
# CMS Admin Registrations
# ============================================================================

@admin.register(CourtPageSettings)
class CourtPageSettingsAdmin(admin.ModelAdmin):
    list_display = ['hero_title', 'show_search', 'show_featured_first', 'is_active', 'updated_at']
    fieldsets = [
        ('Hero Section', {'fields': ['hero_title', 'hero_subtitle', 'banner_image']}),
        ('SEO', {'fields': ['page_title', 'meta_description']}),
        ('Settings', {'fields': ['show_search', 'show_featured_first', 'is_active']}),
        ('Featured Section', {'fields': ['featured_title', 'featured_subtitle']}),
        ('Promo Banner', {'fields': ['promo_banner_title', 'promo_banner_text', 'promo_banner_link', 'promo_banner_image', 'promo_banner_active']}),
    ]
    readonly_fields = ['updated_at']


@admin.register(FeaturedCourt)
class FeaturedCourtAdmin(admin.ModelAdmin):
    list_display = ['court', 'label', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active', 'label']
    list_filter = ['is_active']
    search_fields = ['court__name']

@admin.register(TournamentPageSettings)
class TournamentPageSettingsAdmin(admin.ModelAdmin):
    list_display = ['hero_title', 'announcement_active', 'is_active']
    readonly_fields = ['updated_at']


@admin.register(TournamentCategory)
class TournamentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FeaturedTournament)
class FeaturedTournamentAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'label', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']


@admin.register(TournamentAnnouncement)
class TournamentAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'is_active', 'display_order']
    list_editable = ['is_active', 'display_order']
    list_filter = ['announcement_type', 'is_active']


@admin.register(EquipmentPageSettings)
class EquipmentPageSettingsAdmin(admin.ModelAdmin):
    list_display = ['hero_title', 'show_availability_filter', 'is_active']
    readonly_fields = ['updated_at']


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FeaturedEquipment)
class FeaturedEquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'label', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']


@admin.register(MaintenanceMode)
class MaintenanceModeAdmin(admin.ModelAdmin):
    list_display = ['is_active', 'title', 'estimated_return', 'scheduled_start', 'scheduled_end']
    readonly_fields = ['last_enabled_at', 'last_disabled_at', 'last_enabled_by', 'last_disabled_by', 'updated_at']

    def has_add_permission(self, request):
        return not MaintenanceMode.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MaintenanceAuditLog)
class MaintenanceAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'performed_by', 'created_at']
    list_filter = ['action', 'created_at']
    readonly_fields = ['action', 'performed_by', 'details', 'ip_address', 'created_at']
    search_fields = ['details']


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['footer_email', 'copyright_text', 'is_active']
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'website_url', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    search_fields = ['name']


@admin.register(GlobalAnnouncement)
class GlobalAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'is_active', 'display_order', 'created_at']
    list_editable = ['is_active', 'display_order']
    list_filter = ['announcement_type', 'is_active']


@admin.register(ContentVersion)
class ContentVersionAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'section', 'version_number', 'is_published', 'changed_by', 'created_at']
    list_filter = ['content_type', 'is_published', 'created_at']
    readonly_fields = ['content_type', 'section', 'old_value', 'new_value', 'changed_by', 'version_number', 'is_published', 'created_at']
    search_fields = ['section']


# ============================================================================
# NEW CMS Admin Registrations
# ============================================================================

@admin.register(HeroSectionSettings)
class HeroSectionSettingsAdmin(admin.ModelAdmin):
    list_display = ['background_type', 'badge_text', 'is_active', 'updated_at']
    fieldsets = [
        ('Background', {'fields': ['background_type', 'solid_color', 'gradient_start', 'gradient_end', 'gradient_direction', 'background_image', 'overlay_color', 'overlay_opacity']}),
        ('Content', {'fields': ['badge_text', 'title', 'subtitle']}),
        ('Settings', {'fields': ['show_search_widget', 'min_height', 'is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not HeroSectionSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
    list_display = ['brand_name', 'has_logos_display', 'updated_at']
    fieldsets = [
        ('Brand Identity', {'fields': ['brand_name', 'website_logo', 'header_logo', 'footer_logo']}),
        ('Platform Assets', {'fields': ['favicon', 'login_logo', 'loading_logo', 'email_logo']}),
        ('Status', {'fields': ['is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not SiteBranding.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Has Logos', boolean=True)
    def has_logos_display(self, obj):
        return obj.has_logos


@admin.register(TopBarSettings)
class TopBarSettingsAdmin(admin.ModelAdmin):
    list_display = ['is_visible', 'phone_primary', 'email_primary', 'updated_at']
    fieldsets = [
        ('Visibility', {'fields': ['is_visible', 'show_contact_info', 'show_social_media', 'show_language_selector']}),
        ('Contact Information', {'fields': ['phone_primary', 'phone_secondary', 'email_primary', 'email_secondary', 'office_hours', 'physical_address']}),
        ('Styling', {'fields': ['background_color', 'background_gradient_start', 'background_gradient_end', 'text_color']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not TopBarSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NavBarSettings)
class NavBarSettingsAdmin(admin.ModelAdmin):
    list_display = ['is_sticky', 'brand_text', 'is_active', 'updated_at']
    fieldsets = [
        ('General', {'fields': ['is_sticky', 'show_brand', 'brand_text', 'container_style', 'show_search']}),
        ('Styling', {'fields': ['background_color', 'text_color', 'text_color_hover', 'cta_button_text', 'cta_button_color']}),
        ('Status', {'fields': ['is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not NavBarSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NavBarMenuItem)
class NavBarMenuItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'link_type', 'menu_position', 'is_active', 'display_order']
    list_filter = ['is_active', 'menu_position', 'link_type']
    list_editable = ['is_active', 'display_order', 'menu_position']
    search_fields = ['title']
    ordering = ['menu_position', 'display_order']


@admin.register(FooterSettings)
class FooterSettingsAdmin(admin.ModelAdmin):
    list_display = ['organization_name', 'is_visible', 'show_newsletter', 'updated_at']
    fieldsets = [
        ('General', {'fields': ['is_visible', 'organization_name', 'short_description', 'copyright_text']}),
        ('Sections', {'fields': ['show_quick_links', 'show_contact_details', 'show_social_media', 'show_newsletter']}),
        ('Newsletter', {'fields': ['newsletter_heading', 'newsletter_description', 'newsletter_button_text']}),
        ('Developer Credit', {'fields': ['developer_credit', 'developer_contact', 'version_text']}),
        ('Styling', {'fields': ['background_gradient_start', 'background_gradient_end', 'text_color']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not FooterSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FooterQuickLink)
class FooterQuickLinkAdmin(admin.ModelAdmin):
    list_display = ['title', 'link_type', 'is_active', 'display_order']
    list_filter = ['is_active', 'link_type']
    list_editable = ['is_active', 'display_order']
    search_fields = ['title']
    ordering = ['display_order']


# ============================================================================
# WEBSITE DESIGN CMS Admin Registrations
# ============================================================================

@admin.register(GlobalDesignSettings)
class GlobalDesignSettingsAdmin(admin.ModelAdmin):
    list_display = ['primary_color', 'base_font_size', 'is_active', 'updated_at']
    fieldsets = [
        ('Typography', {'fields': ['heading_font_family', 'body_font_family', 'base_font_size', 'heading_font_weight']}),
        ('Color Scheme', {'fields': ['primary_color', 'primary_hover_color', 'secondary_color', 'accent_color',
                                     'success_color', 'warning_color', 'danger_color', 'info_color',
                                     'text_primary_color', 'text_muted_color', 'background_light_color', 'background_dark_color']}),
        ('Border Radius', {'fields': ['border_radius_sm', 'border_radius_md', 'border_radius_lg', 'border_radius_full']}),
        ('Shadows', {'fields': ['shadow_sm', 'shadow_md', 'shadow_lg']}),
        ('Spacing & Layout', {'fields': ['spacing_unit', 'section_padding', 'container_max_width']}),
        ('Status', {'fields': ['is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not GlobalDesignSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ButtonStyleSettings)
class ButtonStyleSettingsAdmin(admin.ModelAdmin):
    list_display = ['button_border_radius', 'primary_bg', 'is_active', 'updated_at']
    fieldsets = [
        ('General', {'fields': ['button_border_radius', 'button_padding_y', 'button_padding_x',
                                'button_font_weight', 'button_font_size', 'button_text_transform', 'button_letter_spacing']}),
        ('Primary Button', {'fields': ['primary_bg', 'primary_hover_bg', 'primary_text_color']}),
        ('Secondary Button', {'fields': ['secondary_bg', 'secondary_hover_bg', 'secondary_text_color']}),
        ('Outline Button', {'fields': ['outline_border_color', 'outline_hover_bg', 'outline_text_color', 'outline_hover_text_color']}),
        ('Semantic Buttons', {'fields': ['success_bg', 'danger_bg', 'warning_bg', 'info_bg']}),
        ('Size Variants', {'fields': ['btn_lg_padding_y', 'btn_lg_padding_x', 'btn_lg_font_size',
                                      'btn_sm_padding_y', 'btn_sm_padding_x', 'btn_sm_font_size']}),
        ('Status', {'fields': ['is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not ButtonStyleSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CardStyleSettings)
class CardStyleSettingsAdmin(admin.ModelAdmin):
    list_display = ['card_border_radius', 'card_background', 'is_active', 'updated_at']
    fieldsets = [
        ('Default Card', {'fields': ['card_background', 'card_border_radius', 'card_shadow', 'card_hover_shadow',
                                     'card_border', 'card_padding', 'card_margin_bottom']}),
        ('Card Header', {'fields': ['card_header_bg', 'card_header_text_color', 'card_header_padding', 'card_header_border']}),
        ('Card Body', {'fields': ['card_body_padding']}),
        ('Section Containers', {'fields': ['section_bg_light', 'section_bg_dark', 'section_padding']}),
        ('Admin Cards', {'fields': ['admin_card_border_radius', 'admin_card_shadow', 'admin_card_header_bg']}),
        ('Status', {'fields': ['is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not CardStyleSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScrollToTopSettings)
class ScrollToTopSettingsAdmin(admin.ModelAdmin):
    list_display = ['is_visible', 'button_size', 'background_color', 'is_active', 'updated_at']
    fieldsets = [
        ('Visibility', {'fields': ['is_visible']}),
        ('Position', {'fields': ['position_right', 'position_bottom']}),
        ('Size & Appearance', {'fields': ['button_size', 'border_radius', 'icon_class']}),
        ('Colors', {'fields': ['background_color', 'hover_background_color', 'icon_color', 'hover_icon_color']}),
        ('Shadow', {'fields': ['shadow', 'hover_shadow']}),
        ('Behavior', {'fields': ['show_after_scroll', 'scroll_duration']}),
        ('Status', {'fields': ['is_active']}),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not ScrollToTopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SocialPlatformSettings)
class SocialPlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ['platform', 'url_short', 'is_active', 'show_in_topbar', 'show_in_footer', 'display_order']
    list_filter = ['is_active', 'show_in_topbar', 'show_in_footer']
    list_editable = ['is_active', 'show_in_topbar', 'show_in_footer', 'display_order']
    readonly_fields = ['created_at', 'updated_at']

    def url_short(self, obj):
        return obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
    url_short.short_description = 'URL'
