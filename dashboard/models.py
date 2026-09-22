from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


class PricingContent(models.Model):
    """Editable content sections for the pricing page"""
    SECTION_CHOICES = [
        ('hero_badge', 'Hero Badge'),
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('court_rates_title', 'Court Rates Section Title'),
        ('court_rates_subtitle', 'Court Rates Section Subtitle'),
        ('membership_title', 'Membership Section Title'),
        ('membership_subtitle', 'Membership Section Subtitle'),
        ('comparison_title', 'Comparison Table Title'),
        ('comparison_subtitle', 'Comparison Table Subtitle'),
        ('services_title', 'Additional Services Title'),
        ('services_subtitle', 'Additional Services Subtitle'),
        ('faq_title', 'FAQ Section Title'),
        ('faq_subtitle', 'FAQ Section Subtitle'),
        ('cta_title', 'CTA Section Title'),
        ('cta_subtitle', 'CTA Section Subtitle'),
    ]
    
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pricing Page Content'
        verbose_name_plural = 'Pricing Page Contents'
        ordering = ['section']

    def __str__(self):
        return self.get_section_display()


class PricingTier(models.Model):
    """Membership tiers for pricing page"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    period = models.CharField(max_length=50, blank=True, help_text="e.g., 'month', 'year', or leave blank for one-time")
    description = models.TextField(blank=True)
    features = models.JSONField(default=list, help_text="List of features as strings")
    is_recommended = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'price']
        verbose_name = 'Pricing Tier'
        verbose_name_plural = 'Pricing Tiers'

    def __str__(self):
        return self.name


class PricingFAQ(models.Model):
    """FAQ items for pricing page"""
    question = models.CharField(max_length=200)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Pricing FAQ'
        verbose_name_plural = 'Pricing FAQs'

    def __str__(self):
        return self.question


class AboutContent(models.Model):
    """Editable content sections for the about page"""
    SECTION_CHOICES = [
        ('hero_badge', 'Hero Badge'),
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('mission_title', 'Mission Section Title'),
        ('mission_text', 'Mission Text'),
        ('mission_features', 'Mission Features (comma-separated)'),
        ('vision_title', 'Vision Section Title'),
        ('vision_text', 'Vision Text'),
        ('vision_features', 'Vision Features (comma-separated)'),
        ('stats_courts', 'Stats - Courts Label'),
        ('stats_members', 'Stats - Members Label'),
        ('stats_years', 'Stats - Years Label'),
        ('stats_tournaments', 'Stats - Tournaments Label'),
        ('journey_badge', 'Journey Section Badge'),
        ('journey_title', 'Journey Section Title'),
        ('journey_subtitle', 'Journey Section Subtitle'),
        ('team_badge', 'Team Section Badge'),
        ('team_title', 'Team Section Title'),
        ('team_subtitle', 'Team Section Subtitle'),
        ('facilities_badge', 'Facilities Section Badge'),
        ('facilities_title', 'Facilities Section Title'),
        ('facilities_subtitle', 'Facilities Section Subtitle'),
        ('why_badge', 'Why Choose Us Badge'),
        ('why_title', 'Why Choose Us Title'),
        ('why_subtitle', 'Why Choose Us Subtitle'),
        ('gallery_badge', 'Gallery Section Badge'),
        ('gallery_title', 'Gallery Section Title'),
        ('gallery_subtitle', 'Gallery Section Subtitle'),
        ('location_badge', 'Location Section Badge'),
        ('location_title', 'Location Section Title'),
        ('location_description', 'Location Description'),
        ('cta_title', 'CTA Section Title'),
        ('cta_subtitle', 'CTA Section Subtitle'),
    ]
    
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'About Page Content'
        verbose_name_plural = 'About Page Contents'
        ordering = ['section']

    def __str__(self):
        return self.get_section_display()


class Milestone(models.Model):
    """Timeline milestones for about page"""
    year = models.CharField(max_length=20)
    title = models.CharField(max_length=100)
    description = models.TextField()
    color = models.CharField(max_length=50, default='primary', help_text="Bootstrap color name: primary, success, warning, info, danger")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'year']
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'

    def __str__(self):
        return f"{self.year} - {self.title}"


class TeamMember(models.Model):
    """Team members for about page"""
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    bio = models.TextField()
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    color = models.CharField(max_length=50, default='primary', help_text="Bootstrap color name for styling")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'

    def __str__(self):
        return f"{self.name} - {self.role}"


class Facility(models.Model):
    """Facilities for about page"""
    icon = models.CharField(max_length=50, default='fa-check', help_text="Font Awesome icon class")
    title = models.CharField(max_length=100)
    description = models.TextField()
    color = models.CharField(max_length=50, default='primary', help_text="Bootstrap color name")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __str__(self):
        return self.title


class WhyChooseItem(models.Model):
    """Why Choose Us items for about page"""
    icon = models.CharField(max_length=50, default='fa-check', help_text="Font Awesome icon class")
    title = models.CharField(max_length=100)
    description = models.TextField()
    color = models.CharField(max_length=50, default='primary', help_text="Bootstrap color name")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Why Choose Item'
        verbose_name_plural = 'Why Choose Items'

    def __str__(self):
        return self.title


class ContactContent(models.Model):
    """Editable content sections for the contact page"""
    SECTION_CHOICES = [
        ('hero_badge', 'Hero Badge'),
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('phone_label', 'Phone Card Label'),
        ('phone_hours', 'Phone Card Hours'),
        ('email_label', 'Email Card Label'),
        ('email_response', 'Email Response Time'),
        ('visit_label', 'Visit Card Label'),
        ('visit_city', 'Visit City'),
        ('form_title', 'Contact Form Title'),
        ('form_name_label', 'Form - Name Label'),
        ('form_email_label', 'Form - Email Label'),
        ('form_subject_label', 'Form - Subject Label'),
        ('form_message_label', 'Form - Message Label'),
        ('form_submit_text', 'Form Submit Button Text'),
        ('hours_title', 'Business Hours Title'),
        ('quick_links_title', 'Quick Links Title'),
        ('social_title', 'Social Media Title'),
        ('map_badge', 'Map Section Badge'),
        ('map_title', 'Map Section Title'),
        ('map_subtitle', 'Map Section Subtitle'),
        ('getting_here_title', 'Getting Here Title'),
        ('faq_badge', 'FAQ Section Badge'),
        ('faq_title', 'FAQ Section Title'),
        ('faq_subtitle', 'FAQ Section Subtitle'),
        ('cta_title', 'CTA Section Title'),
        ('cta_subtitle', 'CTA Section Subtitle'),
    ]
    
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contact Page Content'
        verbose_name_plural = 'Contact Page Contents'
        ordering = ['section']

    def __str__(self):
        return self.get_section_display()


class ContactInfo(models.Model):
    """Contact information (singleton pattern)"""
    phone = models.CharField(max_length=100, default='09455470173')
    email = models.EmailField(blank=True)
    address = models.TextField(default='Valencia, Negros Oriental, Philippines, 6215')
    city_country = models.CharField(max_length=200, default='Valencia, Negros Oriental, Philippines, 6215')
    google_maps_url = models.URLField(blank=True, max_length=1000, help_text="Google Maps directions URL")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contact Information'
        verbose_name_plural = 'Contact Information'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Contact Information'


class BusinessHour(models.Model):
    """Business hours for contact page"""
    day_range = models.CharField(max_length=100, help_text="e.g., 'Monday - Friday'")
    hours = models.CharField(max_length=100, help_text="e.g., '6:00 AM - 10:00 PM'")
    icon_color = models.CharField(max_length=50, default='primary', help_text="Bootstrap color name")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Business Hour'
        verbose_name_plural = 'Business Hours'

    def __str__(self):
        return f"{self.day_range}: {self.hours}"


class ContactFAQ(models.Model):
    """FAQ items for contact page"""
    question = models.CharField(max_length=200)
    answer = models.TextField()
    icon_color = models.CharField(max_length=50, default='primary', help_text="Bootstrap color name")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Contact FAQ'
        verbose_name_plural = 'Contact FAQs'

    def __str__(self):
        return self.question


class SocialLink(models.Model):
    """Social media links for contact page"""
    platform = models.CharField(max_length=50, choices=[
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
    ])
    url = models.URLField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'platform']
        verbose_name = 'Social Link'
        verbose_name_plural = 'Social Links'

    def __str__(self):
        return self.get_platform_display()

    @property
    def icon_class(self):
        icons = {
            'facebook': 'fab fa-facebook-f',
            'twitter': 'fab fa-twitter',
            'instagram': 'fab fa-instagram',
            'whatsapp': 'fab fa-whatsapp',
            'linkedin': 'fab fa-linkedin-in',
            'youtube': 'fab fa-youtube',
            'tiktok': 'fab fa-tiktok',
        }
        return icons.get(self.platform, 'fas fa-link')

    @property
    def button_class(self):
        classes = {
            'facebook': 'btn-outline-primary',
            'twitter': 'btn-outline-info',
            'instagram': 'btn-outline-danger',
            'whatsapp': 'btn-outline-success',
            'linkedin': 'btn-outline-primary',
            'youtube': 'btn-outline-danger',
            'tiktok': 'btn-outline-dark',
        }
        return classes.get(self.platform, 'btn-outline-secondary')


class Testimonial(models.Model):
    """Customer testimonials for the home page"""
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user who submitted this testimonial (if user-submitted)"
    )
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, help_text="e.g., Regular Member, Tournament Player")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5,
        help_text="Rating from 1 to 5 stars"
    )
    text = models.TextField(help_text="Testimonial content")
    avatar = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(
        default=False,
        help_text="Only approved testimonials are displayed on the homepage"
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'

    def __str__(self):
        status = "✓" if self.is_approved else "⏳"
        return f"{status} {self.name} - {self.rating} stars"

    @property
    def status_display(self):
        if not self.is_approved:
            return "pending"
        return "approved" if self.is_active else "inactive"


class Rating(models.Model):
    """Rating submitted by users after reservation completion"""
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='ratings',
        help_text="The user who submitted this rating"
    )
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='rating',
        help_text="The completed reservation being rated"
    )
    rating = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(
        blank=True,
        null=True,
        max_length=500,
        help_text="Optional comment (max 500 characters)"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured ratings are displayed on the homepage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Rating'
        verbose_name_plural = 'Ratings'
        unique_together = [['user', 'reservation']]

    def __str__(self):
        return f"{self.user.username} - {self.rating} stars for Reservation #{self.reservation.id}"

    @property
    def star_display(self):
        """Returns HTML for star display"""
        return '★' * self.rating + '☆' * (5 - self.rating)


class Amenity(models.Model):
    """Facility amenities displayed on home page"""
    icon = models.CharField(
        max_length=50,
        help_text="Font Awesome icon class, e.g., fa-wifi, fa-car",
        default="fa-check"
    )
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Amenity'
        verbose_name_plural = 'Amenities'

    def __str__(self):
        return self.title


class GalleryImage(models.Model):
    """Gallery images for the home page"""
    image = models.ImageField(upload_to='gallery/')
    title = models.CharField(max_length=100, blank=True)
    alt_text = models.CharField(max_length=200, help_text="Alternative text for accessibility")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Gallery Image'
        verbose_name_plural = 'Gallery Images'

    def __str__(self):
        return self.title or f"Gallery Image {self.id}"

    @property
    def url(self):
        if self.image:
            return self.image.url
        return ''


class HomePageContent(models.Model):
    """Editable content sections for the home page"""
    SECTION_CHOICES = [
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('about_title', 'About Section Title'),
        ('about_text', 'About Section Text'),
        ('cta_title', 'CTA Section Title'),
        ('cta_text', 'CTA Section Text'),
    ]
    
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Home Page Content'
        verbose_name_plural = 'Home Page Contents'

    def __str__(self):
        return self.get_section_display()


class ContactMessage(models.Model):
    """Contact form submissions from users"""
    SUBJECT_CHOICES = [
        ('general_inquiry', 'General Inquiry'),
        ('booking', 'Booking Related'),
        ('feedback', 'Feedback'),
        ('support', 'Technical Support'),
        ('partnership', 'Partnership'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ]
    
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default='general_inquiry')
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_reply = models.TextField(blank=True, null=True, help_text="Admin's reply to this message")
    replied_at = models.DateTimeField(blank=True, null=True, help_text="When the admin replied")
    replied_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replied_messages',
        help_text="Admin user who replied"
    )
    is_read = models.BooleanField(default=False, help_text="Whether admin has read this message")
    user_read_reply = models.BooleanField(default=False, help_text="Whether user has read the admin's reply")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.created_at.strftime('%Y-%m-%d')})"

    @property
    def status_badge_class(self):
        """Return Bootstrap badge class for status"""
        classes = {
            'new': 'bg-primary',
            'read': 'bg-info',
            'replied': 'bg-success',
            'closed': 'bg-secondary',
        }
        return classes.get(self.status, 'bg-secondary')


class AboutGalleryImage(models.Model):
    """Gallery images for the about page facility section"""
    image = models.ImageField(upload_to='about/gallery/')
    title = models.CharField(max_length=100, blank=True)
    alt_text = models.CharField(max_length=200, help_text="Alternative text for accessibility")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'About Gallery Image'
        verbose_name_plural = 'About Gallery Images'
    def __str__(self):
        return self.title or f"About Gallery Image {self.id}"

    @property
    def url(self):
        if self.image:
            return self.image.url
        return ''


# ============================================================================
# COURTS PAGE CMS
# ============================================================================

class CourtPageSettings(models.Model):
    """Settings for the public courts page"""
    hero_title = models.CharField(max_length=200, default='Browse Courts')
    hero_subtitle = models.TextField(blank=True, default='Find the perfect court for your next game')
    page_title = models.CharField(max_length=200, blank=True, help_text='Browser tab title')
    meta_description = models.TextField(blank=True, help_text='SEO meta description')
    banner_image = models.ImageField(upload_to='cms/courts/', blank=True, null=True)
    show_search = models.BooleanField(default=True, help_text='Show/hide the search & filter bar')
    show_featured_first = models.BooleanField(default=True, help_text='Show featured courts before regular list')
    featured_title = models.CharField(max_length=200, blank=True, default='Featured Courts')
    featured_subtitle = models.TextField(blank=True, default='Handpicked courts you might love')
    promo_banner_title = models.CharField(max_length=200, blank=True)
    promo_banner_text = models.TextField(blank=True)
    promo_banner_link = models.URLField(blank=True)
    promo_banner_image = models.ImageField(upload_to='cms/courts/', blank=True, null=True)
    promo_banner_active = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Courts Page Setting'
        verbose_name_plural = 'Courts Page Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Courts Page Settings'


class FeaturedCourt(models.Model):
    """Featured court on the public courts page"""
    court = models.ForeignKey('courts.Court', on_delete=models.CASCADE, related_name='cms_features')
    label = models.CharField(max_length=100, blank=True, help_text='e.g. "Recommended", "Popular", "New"')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Featured Court'
        verbose_name_plural = 'Featured Courts'

    def __str__(self):
        return f"Featured: {self.court.name}"


# ============================================================================
# TOURNAMENTS PAGE CMS
# ============================================================================

class TournamentPageSettings(models.Model):
    """Settings for the public tournaments page"""
    hero_title = models.CharField(max_length=200, default='Tournaments')
    hero_subtitle = models.TextField(blank=True, default='Join exciting pickleball competitions and showcase your skills')
    page_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    banner_image = models.ImageField(upload_to='cms/tournaments/', blank=True, null=True)
    announcement = models.TextField(blank=True, help_text='Global announcement shown at top of tournaments page')
    announcement_active = models.BooleanField(default=False)
    featured_title = models.CharField(max_length=200, blank=True, default='Featured Tournaments')
    featured_subtitle = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tournaments Page Setting'
        verbose_name_plural = 'Tournaments Page Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Tournaments Page Settings'


class TournamentCategory(models.Model):
    """Categories for tournaments"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fa-trophy')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Tournament Category'
        verbose_name_plural = 'Tournament Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class FeaturedTournament(models.Model):
    """Featured tournament on the public page"""
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE, related_name='cms_features')
    label = models.CharField(max_length=100, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Featured Tournament'
        verbose_name_plural = 'Featured Tournaments'

    def __str__(self):
        return f"Featured: {self.tournament.name}"


class TournamentAnnouncement(models.Model):
    """Individual tournament announcements"""
    title = models.CharField(max_length=200)
    message = models.TextField()
    link_url = models.URLField(blank=True, help_text='Optional link for more info')
    link_text = models.CharField(max_length=100, blank=True, default='Learn More')
    announcement_type = models.CharField(max_length=20, choices=[
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Urgent'),
    ], default='info')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Tournament Announcement'
        verbose_name_plural = 'Tournament Announcements'

    def __str__(self):
        return self.title


# ============================================================================
# EQUIPMENT PAGE CMS
# ============================================================================

class EquipmentPageSettings(models.Model):
    """Settings for the public equipment page"""
    hero_title = models.CharField(max_length=200, default='Equipment Rental')
    hero_subtitle = models.TextField(blank=True, default='Browse and rent quality equipment for your games')
    page_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    banner_image = models.ImageField(upload_to='cms/equipment/', blank=True, null=True)
    featured_title = models.CharField(max_length=200, blank=True, default='Featured Equipment')
    featured_subtitle = models.TextField(blank=True)
    show_availability_filter = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Equipment Page Setting'
        verbose_name_plural = 'Equipment Page Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Equipment Page Settings'


class EquipmentCategory(models.Model):
    """Categories for equipment"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fa-tools')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Equipment Category'
        verbose_name_plural = 'Equipment Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class FeaturedEquipment(models.Model):
    """Featured equipment item"""
    equipment = models.ForeignKey('equipment.Equipment', on_delete=models.CASCADE, related_name='cms_features')
    label = models.CharField(max_length=100, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Featured Equipment'
        verbose_name_plural = 'Featured Equipment'

    def __str__(self):
        return f"Featured: {self.equipment.name}"


# ============================================================================
# MAINTENANCE MODE
# ============================================================================

class MaintenanceMode(models.Model):
    """Maintenance mode settings (singleton)"""
    is_active = models.BooleanField(default=False, help_text='Enable/disable maintenance mode')
    title = models.CharField(max_length=200, default='System Under Maintenance')
    message = models.TextField(default='We are performing scheduled maintenance. The system will be back shortly.')
    banner_image = models.ImageField(upload_to='cms/maintenance/', blank=True, null=True)
    estimated_return = models.DateTimeField(blank=True, null=True, help_text='Estimated time when system will be back')
    show_contact_info = models.BooleanField(default=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    scheduled_start = models.DateTimeField(blank=True, null=True, help_text='Scheduled maintenance start time')
    scheduled_end = models.DateTimeField(blank=True, null=True, help_text='Scheduled maintenance end time (auto-disables after this)')
    last_enabled_at = models.DateTimeField(blank=True, null=True)
    last_enabled_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='maintenance_enabled'
    )
    last_disabled_at = models.DateTimeField(blank=True, null=True)
    last_disabled_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='maintenance_disabled'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Maintenance Mode'
        verbose_name_plural = 'Maintenance Mode'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"Maintenance Mode: {'ON' if self.is_active else 'OFF'}"

    def clean(self):
        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_start >= self.scheduled_end:
                raise ValidationError('Scheduled end time must be after start time.')


class MaintenanceAuditLog(models.Model):
    """Audit log for maintenance mode changes"""
    ACTION_CHOICES = [
        ('enabled', 'Maintenance Enabled'),
        ('disabled', 'Maintenance Disabled'),
        ('auto_disabled', 'Auto-Disabled (scheduled end)'),
        ('scheduled', 'Maintenance Scheduled'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Maintenance Audit Log'
        verbose_name_plural = 'Maintenance Audit Logs'

    def __str__(self):
        return f"{self.get_action_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# ============================================================================
# SITE SETTINGS (Footer, Partners, Announcements)
# ============================================================================

class SiteSettings(models.Model):
    """Global site settings (singleton)"""
    # Footer
    footer_tagline = models.TextField(blank=True, default='The ultimate pickleball platform connecting players, courts, and organizations.')
    footer_email = models.EmailField(blank=True)
    footer_phone = models.CharField(max_length=50, blank=True)
    footer_address = models.TextField(blank=True)
    copyright_text = models.CharField(max_length=200, blank=True, default='© PickleSphere. All rights reserved.')
    
    # Statistics configuration (override auto-calculated values)
    override_stat_courts = models.IntegerField(blank=True, null=True, help_text='Override courts count (leave blank for auto)')
    override_stat_players = models.IntegerField(blank=True, null=True, help_text='Override players count')
    override_stat_tournaments = models.IntegerField(blank=True, null=True, help_text='Override tournaments count')
    override_stat_years = models.IntegerField(blank=True, null=True, help_text='Override years operating')
    
    # Partners/Sponsors
    partners_title = models.CharField(max_length=200, blank=True, default='Our Partners')
    partners_subtitle = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Setting'
        verbose_name_plural = 'Site Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Site Settings'


class Partner(models.Model):
    """Partner/Sponsor organizations"""
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='cms/partners/', blank=True, null=True)
    website_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Partner'
        verbose_name_plural = 'Partners'

    def __str__(self):
        return self.name


class GlobalAnnouncement(models.Model):
    """Global announcements shown across the site"""
    title = models.CharField(max_length=200)
    message = models.TextField()
    announcement_type = models.CharField(max_length=20, choices=[
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Urgent'),
    ], default='info')
    link_url = models.URLField(blank=True)
    link_text = models.CharField(max_length=100, blank=True)
    show_on_pages = models.CharField(max_length=200, blank=True, help_text='Comma-separated page names, or leave blank for all pages')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Global Announcement'
        verbose_name_plural = 'Global Announcements'

    def __str__(self):
        return self.title


# ============================================================================
# FAQ PAGE CMS
# ============================================================================

class FAQPageContent(models.Model):
    """Editable content sections for the FAQ page"""
    SECTION_CHOICES = [
        ('hero_badge', 'Hero Badge'),
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('search_placeholder', 'Search Placeholder Text'),
        ('contact_title', 'Still Need Help Title'),
        ('contact_text', 'Still Need Help Text'),
        ('cta_button_text', 'CTA Button Text'),
    ]
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FAQ Page Content'
        verbose_name_plural = 'FAQ Page Contents'
        ordering = ['section']

    def __str__(self):
        return self.get_section_display()


class FAQCategory(models.Model):
    """FAQ categories with questions and answers"""
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='fa-question-circle', help_text='Font Awesome icon class')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'FAQ Category'
        verbose_name_plural = 'FAQ Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class FAQItem(models.Model):
    """Individual FAQ question and answer"""
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='questions')
    question = models.CharField(max_length=300)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FAQ Item'
        verbose_name_plural = 'FAQ Items'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return f"[{self.category.name}] {self.question[:60]}"


# ============================================================================
# TERMS OF SERVICE CMS
# ============================================================================

class TermsContent(models.Model):
    """Editable content sections for the Terms of Service page (singleton)"""
    SECTION_CHOICES = [
        ('hero_badge', 'Hero Badge'),
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('last_updated_text', 'Last Updated Label'),
        ('contact_email', 'Contact Email'),
        ('contact_phone', 'Contact Phone'),
        ('contact_address', 'Contact Address'),
    ]
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Terms of Service Content'
        verbose_name_plural = 'Terms of Service Contents'
        ordering = ['section']

    def __str__(self):
        return self.get_section_display()


class TermsSection(models.Model):
    """Individual sections of the Terms of Service (numbered clauses)"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    icon = models.CharField(max_length=50, default='fa-file-contract', help_text='Font Awesome icon class')
    icon_color = models.CharField(max_length=50, default='primary', help_text='Bootstrap color name')
    section_number = models.PositiveIntegerField(default=1, help_text='Section number (1, 2, 3...) for ordering')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Terms of Service Section'
        verbose_name_plural = 'Terms of Service Sections'
        ordering = ['section_number']

    def __str__(self):
        return f"{self.section_number}. {self.title}"


# ============================================================================
# PRIVACY POLICY CMS
# ============================================================================

class PrivacyContent(models.Model):
    """Editable content sections for the Privacy Policy page"""
    SECTION_CHOICES = [
        ('hero_badge', 'Hero Badge'),
        ('hero_title', 'Hero Title'),
        ('hero_subtitle', 'Hero Subtitle'),
        ('last_updated_text', 'Last Updated Label'),
        ('contact_email', 'Contact Email'),
        ('contact_phone', 'Contact Phone'),
        ('contact_address', 'Contact Address'),
    ]
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Privacy Policy Content'
        verbose_name_plural = 'Privacy Policy Contents'
        ordering = ['section']

    def __str__(self):
        return self.get_section_display()


class PrivacySection(models.Model):
    """Individual sections of the Privacy Policy (numbered clauses)"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    icon = models.CharField(max_length=50, default='fa-shield-alt', help_text='Font Awesome icon class')
    icon_color = models.CharField(max_length=50, default='primary', help_text='Bootstrap color name')
    section_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Privacy Policy Section'
        verbose_name_plural = 'Privacy Policy Sections'
        ordering = ['section_number']

    def __str__(self):
        return f"{self.section_number}. {self.title}"


# ============================================================================
# MEDIA LIBRARY
# ============================================================================

class MediaLibrary(models.Model):
    """Centralized media library for CMS images and files"""
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]
    title = models.CharField(max_length=200, help_text='Display name for the file')
    file = models.FileField(upload_to='media_library/%Y/%m/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='image')
    alt_text = models.CharField(max_length=300, blank=True, help_text='Alt text for accessibility')
    caption = models.TextField(blank=True, help_text='Optional caption')
    file_size = models.PositiveIntegerField(default=0, editable=False, help_text='File size in bytes')
    uploaded_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Media Library Item'
        verbose_name_plural = 'Media Library'
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"Media {self.id}"

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size'):
            self.file_size = self.file.size
        if not self.file_type and self.file:
            ext = self.file.name.split('.')[-1].lower() if '.' in self.file.name else ''
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'):
                self.file_type = 'image'
            elif ext in ('pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'):
                self.file_type = 'document'
        super().save(*args, **kwargs)

    @property
    def url(self):
        return self.file.url if self.file else ''

    @property
    def size_display(self):
        """Human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ============================================================================
# CONTENT VERSION HISTORY
# ============================================================================

class ContentVersion(models.Model):
    """Track content version history for CMS items"""
    CONTENT_TYPE_CHOICES = [
        ('homepage', 'Home Page'),
        ('hero', 'Hero Section'),
        ('branding', 'Website Branding'),
        ('topbar', 'Top Bar'),
        ('navbar', 'Navigation Bar'),
        ('footer', 'Footer'),
        ('about', 'About Page'),
        ('contact', 'Contact Page'),
        ('pricing', 'Pricing Page'),
        ('courts', 'Courts Page'),
        ('tournaments', 'Tournaments Page'),
        ('equipment', 'Equipment Page'),
    ]
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    section = models.CharField(max_length=100, help_text='Which section/content was changed')
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    version_number = models.PositiveIntegerField(help_text='Auto-incrementing version per content_type')
    is_published = models.BooleanField(default=True, help_text='Whether this version was published live')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Content Version'
        verbose_name_plural = 'Content Versions'
        indexes = [
            models.Index(fields=['content_type', '-version_number']),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()} v{self.version_number} - {self.section}"


# ============================================================================
# HERO SECTION CMS
# ============================================================================

class HeroSectionSettings(models.Model):
    """Hero section configuration (singleton)"""
    BACKGROUND_TYPE_CHOICES = [
        ('solid', 'Solid Color'),
        ('gradient', 'Gradient'),
        ('image', 'Background Image'),
    ]
    
    background_type = models.CharField(max_length=20, choices=BACKGROUND_TYPE_CHOICES, default='gradient')
    solid_color = models.CharField(max_length=20, default='#1a3a42', help_text='Solid background color (hex)')
    gradient_start = models.CharField(max_length=20, default='#1a3a42', help_text='Gradient start color (hex)')
    gradient_end = models.CharField(max_length=20, default='#0f172a', help_text='Gradient end color (hex)')
    gradient_direction = models.CharField(max_length=20, default='135deg', help_text='Gradient angle, e.g. 135deg, to right, to bottom')
    background_image = models.ImageField(upload_to='cms/hero/', blank=True, null=True, help_text='Background image (1920x1080 recommended)')
    overlay_color = models.CharField(max_length=20, default='#000000', help_text='Overlay color (hex)')
    overlay_opacity = models.FloatField(default=0.6, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], help_text='Overlay opacity (0.0 - 1.0)')
    badge_text = models.CharField(max_length=100, default='The Ultimate Pickleball Platform', help_text='Hero badge text')
    title = models.CharField(max_length=200, default='Welcome to PickleSphere', help_text='Hero main title')
    subtitle = models.TextField(default='The all-in-one platform connecting pickleball players with courts, tournaments, and organizations nationwide.', help_text='Hero subtitle')
    show_search_widget = models.BooleanField(default=True, help_text='Show the search/availability widget')
    min_height = models.CharField(max_length=20, default='90vh', help_text='Minimum height, e.g. 90vh, 100vh, 600px')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hero Section Setting'
        verbose_name_plural = 'Hero Section Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"Hero Section - {self.get_background_type_display()}"

    @property
    def background_image_url(self):
        """Safely return the background image URL or empty string if no file exists."""
        try:
            if self.background_image and self.background_image.name:
                return self.background_image.url
        except (ValueError, FileNotFoundError):
            pass
        return ''

    def get_background_style(self):
        """Return inline CSS for the hero background."""
        if self.background_type == 'solid':
            return f'background-color: {self.solid_color};'
        elif self.background_type == 'gradient':
            return f'background: linear-gradient({self.gradient_direction}, {self.gradient_start}, {self.gradient_end});'
        elif self.background_type == 'image' and self.background_image:
            overlay = f'rgba({int(self.overlay_color[1:3], 16)}, {int(self.overlay_color[3:5], 16)}, {int(self.overlay_color[5:7], 16)}, {self.overlay_opacity})'
            return f'background: linear-gradient({overlay}, {overlay}), url("{self.background_image_url}") center/cover no-repeat;'
        return 'background: linear-gradient(135deg, #1a3a42 0%, #0f172a 100%);'


# ============================================================================
# WEBSITE BRANDING (Logos, Favicon)
# ============================================================================

class SiteBranding(models.Model):
    """Website branding logos and favicon (singleton)"""
    website_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Website logo (200x200 recommended, square)')
    header_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Header navigation logo (32x32 recommended)')
    footer_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Footer logo (48x48 recommended)')
    favicon = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Browser tab icon / favicon (32x32, .ico or .png)')
    login_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Login page logo (200x200 recommended)')
    loading_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Loading screen logo (optional)')
    email_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Email template logo (optional)')
    brand_name = models.CharField(max_length=100, default='PickleSphere', help_text='Website brand name')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Website Branding'
        verbose_name_plural = 'Website Branding'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"Branding - {self.brand_name}"

    @property
    def has_logos(self):
        """Check if any logos are set."""
        return any([self.website_logo, self.header_logo, self.footer_logo, self.favicon, self.login_logo])

    @property
    def cache_buster(self):
        """Return a version string for cache-busting logo URLs.
        Uses Unix timestamp of updated_at so browsers always fetch
        the latest logo after admin uploads a replacement.
        """
        if self.updated_at:
            return str(int(self.updated_at.timestamp()))
        return '1'


# ============================================================================
# TOP BAR SETTINGS
# ============================================================================

class TopBarSettings(models.Model):
    """Top bar configuration (singleton)"""
    is_visible = models.BooleanField(default=True, help_text='Show/hide the entire top bar')
    show_contact_info = models.BooleanField(default=True, help_text='Show contact info section')
    show_social_media = models.BooleanField(default=True, help_text='Show social media icons')
    show_language_selector = models.BooleanField(default=True, help_text='Show language selector')
    phone_primary = models.CharField(max_length=50, blank=True, default='09455470173', help_text='Primary phone number')
    phone_secondary = models.CharField(max_length=50, blank=True, help_text='Secondary phone number (optional)')
    email_primary = models.EmailField(blank=True, default='picklesphere@gmail.com', help_text='Primary email address')
    email_secondary = models.EmailField(blank=True, help_text='Secondary email address (optional)')
    office_hours = models.CharField(max_length=200, blank=True, default='Mon-Sat, 9AM - 6PM', help_text='Office hours text')
    physical_address = models.TextField(blank=True, help_text='Physical address (optional)')
    background_color = models.CharField(max_length=20, default='#1a3a42', help_text='Top bar background color (hex)')
    background_gradient_start = models.CharField(max_length=20, default='#1a3a42', help_text='Gradient start for modern look')
    background_gradient_end = models.CharField(max_length=20, default='#0f172a', help_text='Gradient end for modern look')
    text_color = models.CharField(max_length=20, default='rgba(255,255,255,0.85)', help_text='Text color')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Top Bar Setting'
        verbose_name_plural = 'Top Bar Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"Top Bar: {'Visible' if self.is_visible else 'Hidden'}"


# ============================================================================
# NAVIGATION BAR SETTINGS
# ============================================================================

class NavBarSettings(models.Model):
    """Navigation bar settings (singleton)"""
    is_sticky = models.BooleanField(default=True, help_text='Make navbar sticky on scroll')
    show_brand = models.BooleanField(default=True, help_text='Show brand name/logo in navbar')
    brand_text = models.CharField(max_length=100, default='PickleSphere', help_text='Brand text shown next to logo')
    background_color = models.CharField(max_length=20, default='#0f172a', help_text='Navbar background color (hex)')
    text_color = models.CharField(max_length=20, default='rgba(255,255,255,0.8)', help_text='Navbar link text color')
    text_color_hover = models.CharField(max_length=20, default='#ffffff', help_text='Navbar link hover color')
    cta_button_text = models.CharField(max_length=50, default='Get Started', help_text='CTA button text for non-logged-in users')
    cta_button_color = models.CharField(max_length=20, default='#3B7A8C', help_text='CTA button background color')
    show_search = models.BooleanField(default=False, help_text='Show search icon in navbar')
    container_style = models.CharField(max_length=10, default='container', help_text='Bootstrap container: container or container-fluid')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Navigation Bar Setting'
        verbose_name_plural = 'Navigation Bar Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"NavBar: {'Sticky' if self.is_sticky else 'Static'}"


class NavBarMenuItem(models.Model):
    """Navigation bar menu items"""
    MENU_POSITION_CHOICES = [
        ('left', 'Left (Main Menu)'),
        ('right', 'Right (Actions)'),
    ]
    LINK_TYPE_CHOICES = [
        ('home', 'Home'),
        ('courts', 'Courts'),
        ('tournaments', 'Tournaments'),
        ('equipment', 'Equipment'),
        ('about', 'About'),
        ('contact', 'Contact'),
        ('pricing', 'Pricing'),
        ('faq', 'FAQ'),
        ('custom', 'Custom URL'),
    ]
    title = models.CharField(max_length=100)
    link_type = models.CharField(max_length=30, choices=LINK_TYPE_CHOICES, default='custom')
    custom_url = models.CharField(max_length=500, blank=True, help_text='Full URL for custom links')
    menu_position = models.CharField(max_length=10, choices=MENU_POSITION_CHOICES, default='left')
    requires_auth = models.BooleanField(default=False, help_text='Only show for authenticated users')
    hide_if_auth = models.BooleanField(default=False, help_text='Hide for authenticated users')
    open_in_new_tab = models.BooleanField(default=False)
    icon_class = models.CharField(max_length=50, blank=True, help_text='Font Awesome icon class')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['menu_position', 'display_order', 'title']
        verbose_name = 'Nav Bar Menu Item'
        verbose_name_plural = 'Nav Bar Menu Items'

    def __str__(self):
        return self.title

    def get_url(self):
        """Resolve URL from link_type or use custom_url."""
        from django.urls import reverse
        url_map = {
            'home': 'home',
            'courts': 'all_courts',
            'tournaments': 'tournament_list',
            'equipment': 'equipment_list',
            'about': 'about',
            'contact': 'contact',
            'pricing': 'pricing',
            'faq': 'faq',
        }
        if self.link_type in url_map:
            try:
                return reverse(url_map[self.link_type])
            except Exception:
                return self.custom_url or '#'
        return self.custom_url or '#'


# ============================================================================
# FOOTER SETTINGS
# ============================================================================

class FooterSettings(models.Model):
    """Footer configuration (singleton)"""
    is_visible = models.BooleanField(default=True, help_text='Show/hide the entire footer')
    organization_name = models.CharField(max_length=100, default='PickleSphere', help_text='Organization name in footer')
    short_description = models.TextField(blank=True, default='The ultimate platform connecting pickleball players with courts, equipment, and tournaments nationwide.')
    copyright_text = models.CharField(max_length=200, blank=True, default='© PickleSphere. All rights reserved.')
    show_newsletter = models.BooleanField(default=True, help_text='Show newsletter subscription section')
    newsletter_heading = models.CharField(max_length=100, default='Newsletter', help_text='Newsletter section heading')
    newsletter_description = models.TextField(blank=True, default='Subscribe to receive special offers, tournament updates, and exclusive deals.')
    newsletter_button_text = models.CharField(max_length=50, default='Subscribe', help_text='Newsletter subscribe button text')
    show_social_media = models.BooleanField(default=True, help_text='Show social media links')
    show_contact_details = models.BooleanField(default=True, help_text='Show contact details column')
    show_quick_links = models.BooleanField(default=True, help_text='Show quick links column')
    developer_credit = models.CharField(max_length=200, blank=True, default='Developed by Kylle Ian D. Acibron', help_text='Developer credit text')
    developer_contact = models.CharField(max_length=200, blank=True, default='kylleacibron@gmail.com', help_text='Developer contact')
    version_text = models.CharField(max_length=50, blank=True, default='1.0.0', help_text='Version text')
    background_gradient_start = models.CharField(max_length=20, default='#1a3a42', help_text='Footer background gradient start')
    background_gradient_end = models.CharField(max_length=20, default='#0d1f23', help_text='Footer background gradient end')
    text_color = models.CharField(max_length=20, default='rgba(255,255,255,0.7)', help_text='Footer text color')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Footer Setting'
        verbose_name_plural = 'Footer Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"Footer: {'Visible' if self.is_visible else 'Hidden'}"


class FooterQuickLink(models.Model):
    """Footer quick links managed through CMS"""
    LINK_TYPE_CHOICES = [
        ('home', 'Home'),
        ('courts', 'Courts / Book a Court'),
        ('tournaments', 'Tournaments'),
        ('equipment', 'Equipment'),
        ('leaderboard', 'Leaderboard'),
        ('about', 'About'),
        ('contact', 'Contact'),
        ('pricing', 'Pricing'),
        ('privacy', 'Privacy Policy'),
        ('terms', 'Terms of Service'),
        ('faq', 'FAQ'),
        ('custom', 'Custom URL'),
    ]
    title = models.CharField(max_length=100)
    link_type = models.CharField(max_length=30, choices=LINK_TYPE_CHOICES, default='custom')
    custom_url = models.CharField(max_length=500, blank=True, help_text='Full URL for custom links')
    open_in_new_tab = models.BooleanField(default=False)
    icon_class = models.CharField(max_length=50, blank=True, help_text='Optional Font Awesome icon')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Footer Quick Link'
        verbose_name_plural = 'Footer Quick Links'

    def __str__(self):
        return self.title

    def get_url(self):
        """Resolve URL from link_type or use custom_url."""
        from django.urls import reverse
        url_map = {
            'home': 'home',
            'courts': 'court_list',
            'tournaments': 'tournament_list',
            'equipment': 'equipment_list',
            'leaderboard': 'leaderboard',
            'about': 'about',
            'contact': 'contact',
            'pricing': 'pricing',
            'privacy': 'privacy_policy',
            'terms': 'terms_of_service',
            'faq': 'faq',
        }
        if self.link_type in url_map:
            try:
                return reverse(url_map[self.link_type])
            except Exception:
                return self.custom_url or '#'
        return self.custom_url or '#'


# ============================================================================
# SOCIAL MEDIA PLATFORM SETTINGS
# ============================================================================

class SocialPlatformSettings(models.Model):
    """Social media platform configuration for top bar and footer"""
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('twitter', 'X (Twitter)'),
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('telegram', 'Telegram'),
        ('messenger', 'Messenger'),
    ]
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES, unique=True)
    url = models.URLField(blank=True, help_text='Social media profile URL')
    is_active = models.BooleanField(default=True, help_text='Show/hide this social media icon')
    show_in_topbar = models.BooleanField(default=True, help_text='Show in top bar')
    show_in_footer = models.BooleanField(default=True, help_text='Show in footer')
    open_in_new_tab = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'platform']
        verbose_name = 'Social Media Platform'
        verbose_name_plural = 'Social Media Platforms'

    def __str__(self):
        return self.get_platform_display()

    @property
    def icon_class(self):
        icons = {
            'facebook': 'fab fa-facebook-f',
            'twitter': 'fab fa-x-twitter',
            'instagram': 'fab fa-instagram',
            'whatsapp': 'fab fa-whatsapp',
            'linkedin': 'fab fa-linkedin-in',
            'youtube': 'fab fa-youtube',
            'tiktok': 'fab fa-tiktok',
            'telegram': 'fab fa-telegram-plane',
            'messenger': 'fab fa-facebook-messenger',
        }
        return icons.get(self.platform, 'fas fa-link')


# ============================================================================
# GLOBAL DESIGN SYSTEM (Typography, Colors, Shadows)
# ============================================================================

class GlobalDesignSettings(models.Model):
    """Global visual design settings (singleton) — typography, colors, spacing."""
    heading_font_family = models.CharField(max_length=200, default="'Inter', -apple-system, BlinkMacSystemFont, sans-serif", help_text='Heading font family (CSS)')
    body_font_family = models.CharField(max_length=200, default="'Inter', -apple-system, BlinkMacSystemFont, sans-serif", help_text='Body font family (CSS)')
    base_font_size = models.CharField(max_length=20, default='16px', help_text='Base font size for body text')
    heading_font_weight = models.CharField(max_length=20, default='700', help_text='Heading font weight (e.g. 400, 600, 700)')
    primary_color = models.CharField(max_length=20, default='#3B7A8C', help_text='Primary brand color')
    primary_hover_color = models.CharField(max_length=20, default='#2d5f6e', help_text='Primary hover/dark variant')
    secondary_color = models.CharField(max_length=20, default='#1a3a42', help_text='Secondary brand color')
    accent_color = models.CharField(max_length=20, default='#4A9DA8', help_text='Accent/highlight color')
    success_color = models.CharField(max_length=20, default='#28a745', help_text='Success/positive color')
    warning_color = models.CharField(max_length=20, default='#ffc107', help_text='Warning color')
    danger_color = models.CharField(max_length=20, default='#dc3545', help_text='Danger/error color')
    info_color = models.CharField(max_length=20, default='#17a2b8', help_text='Info color')
    text_primary_color = models.CharField(max_length=20, default='#212529', help_text='Primary text color')
    text_muted_color = models.CharField(max_length=20, default='#6c757d', help_text='Muted/secondary text color')
    background_light_color = models.CharField(max_length=20, default='#f8f9fa', help_text='Light section background')
    background_dark_color = models.CharField(max_length=20, default='#0f172a', help_text='Dark section background')
    border_radius_sm = models.CharField(max_length=20, default='6px', help_text='Small border radius')
    border_radius_md = models.CharField(max_length=20, default='12px', help_text='Medium border radius')
    border_radius_lg = models.CharField(max_length=20, default='20px', help_text='Large border radius')
    border_radius_full = models.CharField(max_length=20, default='50px', help_text='Full/pill border radius')
    shadow_sm = models.CharField(max_length=200, default='0 2px 8px rgba(0,0,0,0.05)', help_text='Small shadow (CSS box-shadow)')
    shadow_md = models.CharField(max_length=200, default='0 4px 16px rgba(0,0,0,0.08)', help_text='Medium shadow (CSS box-shadow)')
    shadow_lg = models.CharField(max_length=200, default='0 8px 30px rgba(0,0,0,0.12)', help_text='Large shadow (CSS box-shadow)')
    spacing_unit = models.CharField(max_length=20, default='8px', help_text='Base spacing unit used for margins/padding')
    section_padding = models.CharField(max_length=20, default='5rem 0', help_text='Default section vertical padding')
    container_max_width = models.CharField(max_length=20, default='1200px', help_text='Max container width')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Global Design Setting'
        verbose_name_plural = 'Global Design Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Global Design Settings'

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB comma-separated string (e.g. '#3B7A8C' -> '59, 122, 140')."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f'{r}, {g}, {b}'
        return '59, 122, 140'  # fallback to default

    def get_css_variables(self):
        """Return a CSS custom properties string for injection into templates."""
        return f'''
:root {{
  --primary-color: {self.primary_color};
  --primary-rgb: {self._hex_to_rgb(self.primary_color)};
  --primary-hover: {self.primary_hover_color};
  --secondary-color: {self.secondary_color};
  --accent-color: {self.accent_color};
  --success-color: {self.success_color};
  --warning-color: {self.warning_color};
  --danger-color: {self.danger_color};
  --info-color: {self.info_color};
  --text-primary: {self.text_primary_color};
  --text-muted: {self.text_muted_color};
  --bg-light: {self.background_light_color};
  --bg-dark: {self.background_dark_color};
  --border-radius-sm: {self.border_radius_sm};
  --border-radius-md: {self.border_radius_md};
  --border-radius-lg: {self.border_radius_lg};
  --border-radius-full: {self.border_radius_full};
  --shadow-sm: {self.shadow_sm};
  --shadow-md: {self.shadow_md};
  --shadow-lg: {self.shadow_lg};
  --spacing-unit: {self.spacing_unit};
  --section-padding: {self.section_padding};
  --container-max-width: {self.container_max_width};
  --heading-font: {self.heading_font_family};
  --body-font: {self.body_font_family};
  --base-font-size: {self.base_font_size};
  --heading-font-weight: {self.heading_font_weight};
}}'''


# ============================================================================
# BUTTON STYLE SETTINGS
# ============================================================================

class ButtonStyleSettings(models.Model):
    """Global button style configuration (singleton)."""
    button_border_radius = models.CharField(max_length=20, default='8px', help_text='Button border radius')
    button_padding_y = models.CharField(max_length=20, default='0.625rem', help_text='Button vertical padding')
    button_padding_x = models.CharField(max_length=20, default='1.5rem', help_text='Button horizontal padding')
    button_font_weight = models.CharField(max_length=20, default='600', help_text='Button font weight')
    button_font_size = models.CharField(max_length=20, default='0.875rem', help_text='Button font size')
    button_text_transform = models.CharField(max_length=50, default='none', help_text='Text transform (none, uppercase, capitalize)')
    button_letter_spacing = models.CharField(max_length=20, default='0.3px', help_text='Letter spacing')
    primary_bg = models.CharField(max_length=20, default='#3B7A8C', help_text='Primary button background')
    primary_hover_bg = models.CharField(max_length=20, default='#2d5f6e', help_text='Primary button hover background')
    primary_text_color = models.CharField(max_length=20, default='#ffffff', help_text='Primary button text color')
    secondary_bg = models.CharField(max_length=20, default='#6c757d', help_text='Secondary button background')
    secondary_hover_bg = models.CharField(max_length=20, default='#5a6268', help_text='Secondary button hover background')
    secondary_text_color = models.CharField(max_length=20, default='#ffffff', help_text='Secondary button text color')
    outline_border_color = models.CharField(max_length=20, default='#3B7A8C', help_text='Outline button border color')
    outline_hover_bg = models.CharField(max_length=20, default='#3B7A8C', help_text='Outline button hover background')
    outline_text_color = models.CharField(max_length=20, default='#3B7A8C', help_text='Outline button text color')
    outline_hover_text_color = models.CharField(max_length=20, default='#ffffff', help_text='Outline button hover text color')
    success_bg = models.CharField(max_length=20, default='#28a745', help_text='Success button background')
    danger_bg = models.CharField(max_length=20, default='#dc3545', help_text='Danger button background')
    warning_bg = models.CharField(max_length=20, default='#ffc107', help_text='Warning button background')
    info_bg = models.CharField(max_length=20, default='#17a2b8', help_text='Info button background')
    btn_lg_padding_y = models.CharField(max_length=20, default='0.75rem', help_text='Large button vertical padding')
    btn_lg_padding_x = models.CharField(max_length=20, default='2rem', help_text='Large button horizontal padding')
    btn_lg_font_size = models.CharField(max_length=20, default='1rem', help_text='Large button font size')
    btn_sm_padding_y = models.CharField(max_length=20, default='0.375rem', help_text='Small button vertical padding')
    btn_sm_padding_x = models.CharField(max_length=20, default='1rem', help_text='Small button horizontal padding')
    btn_sm_font_size = models.CharField(max_length=20, default='0.8rem', help_text='Small button font size')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Button Style Setting'
        verbose_name_plural = 'Button Style Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Button Style Settings'


# ============================================================================
# CARD / SECTION STYLE SETTINGS
# ============================================================================

class CardStyleSettings(models.Model):
    """Global card and section container styling (singleton)."""
    card_background = models.CharField(max_length=20, default='#ffffff', help_text='Card background color')
    card_border_radius = models.CharField(max_length=20, default='12px', help_text='Card border radius')
    card_shadow = models.CharField(max_length=200, default='0 2px 8px rgba(0,0,0,0.05)', help_text='Card box shadow')
    card_hover_shadow = models.CharField(max_length=200, default='0 8px 30px rgba(0,0,0,0.12)', help_text='Card hover box shadow')
    card_border = models.CharField(max_length=20, default='1px solid #e9ecef', help_text='Card border')
    card_padding = models.CharField(max_length=20, default='1.5rem', help_text='Card inner padding')
    card_margin_bottom = models.CharField(max_length=20, default='1.5rem', help_text='Card bottom margin')
    card_header_bg = models.CharField(max_length=20, default='#f8f9fa', help_text='Card header background')
    card_header_text_color = models.CharField(max_length=20, default='#212529', help_text='Card header text color')
    card_header_padding = models.CharField(max_length=20, default='1rem 1.5rem', help_text='Card header padding')
    card_header_border = models.CharField(max_length=20, default='1px solid #e9ecef', help_text='Card header bottom border')
    card_body_padding = models.CharField(max_length=20, default='1.5rem', help_text='Card body padding')
    section_bg_light = models.CharField(max_length=20, default='#f8f9fa', help_text='Light section background')
    section_bg_dark = models.CharField(max_length=20, default='#0f172a', help_text='Dark section background')
    section_padding = models.CharField(max_length=20, default='4rem 0', help_text='Section vertical padding')
    admin_card_border_radius = models.CharField(max_length=20, default='12px', help_text='Admin card border radius')
    admin_card_shadow = models.CharField(max_length=200, default='0 2px 8px rgba(0,0,0,0.05)', help_text='Admin card shadow')
    admin_card_header_bg = models.CharField(max_length=20, default='#f8f9fa', help_text='Admin card header background')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Card Style Setting'
        verbose_name_plural = 'Card Style Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return 'Card Style Settings'


# ============================================================================
# SCROLL TO TOP BUTTON SETTINGS
# ============================================================================

class ScrollToTopSettings(models.Model):
    """Scroll-to-top button configuration (singleton)."""
    is_visible = models.BooleanField(default=True, help_text='Show the scroll-to-top button')
    position_right = models.CharField(max_length=20, default='2rem', help_text='Distance from right edge')
    position_bottom = models.CharField(max_length=20, default='2rem', help_text='Distance from bottom edge')
    SIZE_CHOICES = [
        ('sm', 'Small (36px)'),
        ('md', 'Medium (44px)'),
        ('lg', 'Large (52px)'),
    ]
    button_size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='md', help_text='Button size')
    background_color = models.CharField(max_length=20, default='#3B7A8C', help_text='Button background color')
    hover_background_color = models.CharField(max_length=20, default='#2d5f6e', help_text='Button hover background color')
    icon_color = models.CharField(max_length=20, default='#ffffff', help_text='Icon color')
    hover_icon_color = models.CharField(max_length=20, default='#ffffff', help_text='Icon hover color')
    border_radius = models.CharField(max_length=20, default='50%', help_text='Button border radius')
    show_after_scroll = models.PositiveIntegerField(default=300, help_text='Show after scrolling this many pixels')
    scroll_duration = models.PositiveIntegerField(default=500, help_text='Scroll animation duration in ms')
    icon_class = models.CharField(max_length=50, default='fas fa-arrow-up', help_text='Font Awesome icon class')
    shadow = models.CharField(max_length=200, default='0 4px 16px rgba(0,0,0,0.2)', help_text='Button shadow')
    hover_shadow = models.CharField(max_length=200, default='0 6px 24px rgba(0,0,0,0.3)', help_text='Button hover shadow')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Scroll to Top Setting'
        verbose_name_plural = 'Scroll to Top Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def __str__(self):
        return f"Scroll to Top: {'Visible' if self.is_visible else 'Hidden'}"

    @property
    def size_px(self):
        sizes = {'sm': '36px', 'md': '44px', 'lg': '52px'}
        return sizes.get(self.button_size, '44px')

    @property
    def icon_size(self):
        sizes = {'sm': '14px', 'md': '18px', 'lg': '22px'}
        return sizes.get(self.button_size, '18px')

    def get_inline_style(self):
        size = self.size_px
        return f'''
#scrollToTop {{
    position: fixed;
    right: {self.position_right};
    bottom: {self.position_bottom};
    width: {size};
    height: {size};
    background: {self.background_color};
    color: {self.icon_color};
    border: none;
    border-radius: {self.border_radius};
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    box-shadow: {self.shadow};
    transition: all 0.3s ease;
    font-size: {self.icon_size};
}}
#scrollToTop:hover {{
    background: {self.hover_background_color};
    color: {self.hover_icon_color};
    box-shadow: {self.hover_shadow};
    transform: translateY(-3px);
}}
#scrollToTop.visible {{
    display: flex;
}}'''

