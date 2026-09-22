"""Shared imports, constants and cross-cutting helpers.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from dashboard.models import BusinessHour
from dashboard.models import ContactContent
from dashboard.models import ContactFAQ
from dashboard.models import ContactInfo as CI
from dashboard.models import ContentVersion
from dashboard.models import SocialLink


STATIC_CONTACT_PHONE = '09455470173'


STATIC_CONTACT_EMAIL = 'picklesphere@gmail.com'


# Helper to get contact info from DB or fallback to static defaults
def _get_contact_info():
    ci = CI.objects.first()
    if ci:
        return {
            'phone': ci.phone or STATIC_CONTACT_PHONE,
            'email': ci.email or STATIC_CONTACT_EMAIL,
            'address': ci.address or '123 Sports Avenue, Makati City',
            'city_country': ci.city_country or 'Metro Manila, Philippines',
            'google_maps_url': getattr(ci, 'google_maps_url', ''),
        }
    return None


def _get_contact_page_data():
    """Build the full contact page payload from the database.
    Cached under 'contact_page_data' and invalidated whenever any contact CMS
    model changes (see dashboard/cache_signals.py)."""

    # Get content from database with fallback defaults
    def get_content(section, default):
        content = ContactContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    content = {
        'hero_badge': get_content('hero_badge', "We're Here to Help"),
        'hero_title': get_content('hero_title', 'Get in Touch'),
        'hero_subtitle': get_content('hero_subtitle', "We'd love to hear from you. Reach out for any questions, inquiries, or just to say hello!"),
        'phone_label': get_content('phone_label', 'Phone'),
        'phone_hours': get_content('phone_hours', 'Mon-Sat, 9AM - 6PM'),
        'email_label': get_content('email_label', 'Email Us'),
        'email_response': get_content('email_response', 'We reply within 24 hours'),
        'visit_label': get_content('visit_label', 'Our Office'),
        'visit_city': get_content('visit_city', ''),
        'form_title': get_content('form_title', 'Send us a Message'),
        'form_name_label': get_content('form_name_label', 'Your Name'),
        'form_email_label': get_content('form_email_label', 'Email Address'),
        'form_subject_label': get_content('form_subject_label', 'Subject'),
        'form_message_label': get_content('form_message_label', 'Message'),
        'form_submit_text': get_content('form_submit_text', 'Send Message'),
        'hours_title': get_content('hours_title', 'Platform Support Hours'),
        'quick_links_title': get_content('quick_links_title', 'Quick Links'),
        'social_title': get_content('social_title', 'Follow Us'),
        'faq_badge': get_content('faq_badge', 'FAQ'),
        'faq_title': get_content('faq_title', 'Frequently Asked Questions'),
        'faq_subtitle': get_content('faq_subtitle', 'Quick answers to common questions'),
        'cta_title': get_content('cta_title', 'Ready to Start Playing?'),
        'cta_subtitle': get_content('cta_subtitle', 'Join thousands of players enjoying pickleball through our platform. Find courts, join tournaments, and connect with the community!'),
    }

    # Get contact info from database or create default
    contact_info_obj = CI.objects.first()
    if contact_info_obj:
        contact_info = {
            'phone': STATIC_CONTACT_PHONE,
            'email': STATIC_CONTACT_EMAIL,
            'address': contact_info_obj.address,
            'city_country': contact_info_obj.city_country,
            'google_maps_url': contact_info_obj.google_maps_url,
        }
    else:
        # Fallback default contact info
        contact_info = {
            'phone': STATIC_CONTACT_PHONE,
            'email': STATIC_CONTACT_EMAIL,
            'address': '123 Sports Avenue, Makati City',
            'city_country': 'Metro Manila, Philippines',
            'google_maps_url': 'https://maps.google.com/?q=14.5547,121.0244',
        }

    # Get business hours from database or use defaults
    db_hours = BusinessHour.objects.filter(is_active=True).order_by('display_order')
    if db_hours.exists():
        business_hours = db_hours
    else:
        # Fallback default business hours
        business_hours = [
            {'day_range': 'Monday - Friday', 'hours': '6:00 AM - 10:00 PM', 'icon_color': 'primary'},
            {'day_range': 'Saturday', 'hours': '6:00 AM - 10:00 PM', 'icon_color': 'success'},
            {'day_range': 'Sunday', 'hours': '7:00 AM - 9:00 PM', 'icon_color': 'warning'},
            {'day_range': 'Holidays', 'hours': '8:00 AM - 8:00 PM', 'icon_color': 'danger'},
        ]

    # Get FAQs from database or use defaults
    db_faqs = ContactFAQ.objects.filter(is_active=True).order_by('display_order')
    if db_faqs.exists():
        faqs = db_faqs
    else:
        # Fallback default FAQs
        faqs = [
            {'question': 'How do I book a court?', 'answer': 'You can easily book a court through our online booking system. Create an account, select your preferred date and time, and complete the payment.', 'icon_color': 'primary'},
            {'question': 'Can I rent equipment?', 'answer': 'Yes! We offer paddle and ball rentals at affordable rates. Members enjoy free equipment rental as part of their membership benefits.', 'icon_color': 'success'},
            {'question': 'Do you offer coaching?', 'answer': 'Absolutely! We have certified pickleball coaches available for private and group lessons. Contact us to schedule a session.', 'icon_color': 'warning'},
            {'question': 'How do I join tournaments?', 'answer': 'Tournament registration is done through our website. Navigate to the Tournaments page, select an event, and click Register to join.', 'icon_color': 'info'},
        ]

    # Get social links from database or use defaults
    db_socials = SocialLink.objects.filter(is_active=True).order_by('display_order')
    if db_socials.exists():
        social_links = db_socials
    else:
        # Fallback default social links (empty - no social links shown)
        social_links = []

    return {
        'content': content,
        'contact_info': contact_info,
        'business_hours': business_hours,
        'faqs': faqs,
        'social_links': social_links,
    }


def _log_version(content_type, section, old_value, new_value, user, is_published=True):
    """Log a content version entry."""
    last_version = ContentVersion.objects.filter(content_type=content_type).first()
    version_number = (last_version.version_number + 1) if last_version else 1
    ContentVersion.objects.create(
        content_type=content_type,
        section=section,
        old_value=str(old_value)[:5000],
        new_value=str(new_value)[:5000],
        changed_by=user,
        version_number=version_number,
        is_published=is_published,
    )


# ============================================================================
# COURTS PAGE CMS
# ============================================================================
