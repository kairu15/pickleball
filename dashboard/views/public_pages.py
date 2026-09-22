"""Public marketing pages (courts, pricing, about, contact, legal, FAQ).

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.models import User
from courts.models import Court
from courts.models import Site
from dashboard.cache_utils import PAGES_CACHE_TIMEOUT
from dashboard.cache_utils import cache_anon_page
from dashboard.cache_utils import pages_cache_get_or_set
from dashboard.models import AboutContent
from dashboard.models import AboutGalleryImage
from dashboard.models import ContactMessage
from dashboard.models import FAQCategory
from dashboard.models import FAQPageContent
from dashboard.models import PricingContent
from dashboard.models import PricingFAQ
from dashboard.models import PricingTier
from dashboard.models import PrivacyContent
from dashboard.models import PrivacySection
from dashboard.models import Rating
from dashboard.models import TermsContent
from dashboard.models import TermsSection
from dashboard.views.shared import STATIC_CONTACT_EMAIL
from dashboard.views.shared import STATIC_CONTACT_PHONE
from dashboard.views.shared import _get_contact_info
from dashboard.views.shared import _get_contact_page_data
from datetime import datetime
from django.contrib import messages
from django.db.models import Avg
from django.db.models import FloatField
from django.db.models import OuterRef
from django.db.models import Subquery
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from notifications.email_utils import send_contact_form_email
from reservations.models import Reservation
from tournaments.models import Tournament


def all_courts_view(request):
    """All courts page - accessible to all users"""

    # Annotate average rating on courts queryset
    rating_subq = Rating.objects.filter(
        reservation__court=OuterRef('pk')
    ).values('reservation__court').annotate(
        avg=Avg('rating')
    ).values('avg')

    courts = Court.objects.filter(is_active=True).select_related('site').annotate(
        rating_avg=Subquery(rating_subq, output_field=FloatField())
    )
    sites = Site.objects.filter(is_active=True)

    site_id = request.GET.get('site', '')
    if site_id:
        courts = courts.filter(site_id=site_id)

    court_type = request.GET.get('type', '')
    if court_type:
        courts = courts.filter(court_type=court_type)

    date = request.GET.get('date', '')
    if date:
        try:
            selected_date = datetime.strptime(date, '%Y-%m-%d').date()
            reserved_court_ids = Reservation.objects.filter(
                date=selected_date,
                status__in=['confirmed', 'pending']
            ).values_list('court_id', flat=True)
            courts = courts.exclude(id__in=reserved_court_ids)
        except ValueError:
            pass

    return render(request, 'public/courts/all_courts.html', {
        'courts': courts,
        'sites': sites,
        'selected_site': site_id,
        'selected_type': court_type,
        'selected_date': date,
    })


def court_view_view(request, court_id):
    """Court detail page - accessible to all users"""

    court = get_object_or_404(Court, id=court_id, is_active=True)

    today = datetime.now().date()
    upcoming_reservations = Reservation.objects.filter(
        court=court,
        date__gte=today,
        status__in=['confirmed', 'pending']
    ).order_by('date', 'start_time')[:10]

    return render(request, 'public/courts/court_view.html', {
        'court': court,
        'upcoming_reservations': upcoming_reservations
    })


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='pricing')
def pricing_view(request):
    """Pricing page - accessible to all users (cached for anonymous visitors)"""

    courts = Court.objects.filter(is_active=True)

    # Get content from database with fallback defaults
    def get_content(section, default):
        content = PricingContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    content = {
        'hero_badge': get_content('hero_badge', 'Transparent Pricing'),
        'hero_title': get_content('hero_title', 'Simple, Fair Pricing'),
        'hero_subtitle': get_content('hero_subtitle', 'Choose the perfect plan for your pickleball journey. No hidden fees, no surprises.'),
        'court_rates_title': get_content('court_rates_title', 'Hourly Court Rates'),
        'court_rates_subtitle': get_content('court_rates_subtitle', 'Premium courts at competitive prices'),
        'membership_title': get_content('membership_title', 'Membership Plans'),
        'membership_subtitle': get_content('membership_subtitle', 'Save more with our exclusive membership options'),
        'comparison_title': get_content('comparison_title', 'Compare Plans'),
        'comparison_subtitle': get_content('comparison_subtitle', 'Find the perfect fit for your needs'),
        'services_title': get_content('services_title', 'Equipment & Services'),
        'services_subtitle': get_content('services_subtitle', 'Everything you need for the perfect game'),
        'faq_title': get_content('faq_title', 'Frequently Asked Questions'),
        'faq_subtitle': get_content('faq_subtitle', 'Got questions? We\'ve got answers'),
        'cta_title': get_content('cta_title', 'Ready to Start Playing?'),
        'cta_subtitle': get_content('cta_subtitle', 'Book a court today and experience the best pickleball facility in town.'),
    }

    # Calculate pricing tiers based on court types
    standard_courts = courts.filter(court_type='standard')
    premium_courts = courts.filter(court_type='premium')
    indoor_courts = courts.filter(court_type='indoor')

    pricing_data = {
        'standard_rate': 200 if standard_courts.exists() else 200,
        'premium_rate': 350 if premium_courts.exists() else 350,
        'indoor_rate': 300 if indoor_courts.exists() else 300,
    }

    # Get membership tiers from database or use defaults
    db_tiers = PricingTier.objects.filter(is_active=True).order_by('display_order', 'price')
    if db_tiers.exists():
        membership_tiers = []
        for tier in db_tiers:
            membership_tiers.append({
                'name': tier.name,
                'price': float(tier.price),
                'period': tier.period,
                'features': tier.features,
                'recommended': tier.is_recommended
            })
    else:
        # Fallback default membership tiers
        membership_tiers = [
            {
                'name': 'Basic',
                'price': 0,
                'features': ['Court booking access', 'Online reservations', 'Basic equipment rental', 'No priority booking', 'No member discounts'],
                'recommended': False
            },
            {
                'name': 'Pro Member',
                'price': 400,
                'period': 'month',
                'features': ['All Basic features', '10% off court rentals', 'Priority booking', 'Free paddle rental', 'Tournament discounts'],
                'recommended': True
            },
            {
                'name': 'Elite',
                'price': 350,
                'period': 'month',
                'features': ['All Pro features', '20% off court rentals', 'Unlimited bookings', 'Free equipment use', 'Coaching sessions'],
                'recommended': False
            }
        ]

    # Get FAQs from database or use defaults
    db_faqs = PricingFAQ.objects.filter(is_active=True).order_by('display_order', '-created_at')
    if db_faqs.exists():
        faqs = db_faqs[:4]  # Get first 4 active FAQs
    else:
        # Fallback default FAQs
        faqs = [
            {
                'question': 'Can I cancel my booking?',
                'answer': 'Yes, you can cancel up to 24 hours before your scheduled time for a full refund. Cancellations within 24 hours may be subject to a fee.'
            },
            {
                'question': 'Do memberships auto-renew?',
                'answer': 'Yes, monthly memberships auto-renew unless cancelled. You can cancel anytime from your account settings.'
            },
            {
                'question': 'Can I upgrade my membership?',
                'answer': 'Absolutely! You can upgrade your membership at any time. The price difference will be prorated for the remaining period.'
            },
            {
                'question': 'Are there any hidden fees?',
                'answer': 'No hidden fees! The prices shown are exactly what you\'ll pay. Equipment rental and other services are clearly priced.'
            },
        ]

    return render(request, 'public/pricing.html', {
        'pricing': pricing_data,
        'content': content,
        'membership_tiers': membership_tiers,
        'faqs': faqs,
        'courts': courts
    })


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='about')
def about_view(request):
    """About page - accessible to all users (cached for anonymous visitors)"""

    # Get content from database with fallback defaults
    def get_content(section, default):
        content = AboutContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default

    # Get contact info from database or use defaults
    contact_info = _get_contact_info()
    if not contact_info:
        contact_info = {
            'phone': STATIC_CONTACT_PHONE,
            'email': STATIC_CONTACT_EMAIL,
            'address': '123 Sports Avenue, Makati City',
            'city_country': 'Metro Manila, Philippines',
        }

    content = {
        'hero_badge': get_content('hero_badge', 'Our Story'),
        'hero_title': get_content('hero_title', 'Welcome to PickleSphere'),
        'hero_subtitle': get_content('hero_subtitle', 'The Philippines\' premier pickleball platform, connecting players with courts, tournaments, and equipment nationwide.'),
        'mission_title': get_content('mission_title', 'Our Mission'),
        'mission_text': get_content('mission_text', 'To grow the sport of pickleball by providing a centralized platform that connects players with organizations, simplifies court reservations, streamlines tournament management, and fosters a vibrant, inclusive pickleball community across the Philippines.'),
        'mission_features': get_content('mission_features', 'Connect players to courts,Simplify court reservations,Streamline tournaments,Build community').split(','),
        'vision_title': get_content('vision_title', 'Our Vision'),
        'vision_text': get_content('vision_text', 'To become the leading pickleball ecosystem in Southeast Asia, where every player can easily find a court, join a tournament, and be part of a thriving community.'),
        'vision_features': get_content('vision_features', 'Leading ecosystem,Accessible to all,Empower players,Grow the sport').split(','),
        'stats_courts': get_content('stats_courts', 'Courts on Platform'),
        'stats_members': get_content('stats_members', 'Active Players'),
        'stats_years': get_content('stats_years', 'Years in Operation'),
        'stats_tournaments': get_content('stats_tournaments', 'Tournaments Hosted'),
        'offers_badge': get_content('offers_badge', 'WHAT WE OFFER'),
        'offers_title': get_content('offers_title', 'Platform Features'),
        'offers_subtitle': get_content('offers_subtitle', 'Everything you need for the perfect pickleball experience'),
        'howitworks_badge': get_content('howitworks_badge', 'HOW IT WORKS'),
        'howitworks_title': get_content('howitworks_title', 'Getting Started is Easy'),
        'howitworks_subtitle': get_content('howitworks_subtitle', 'Follow these simple steps to start playing'),
        'players_badge': get_content('players_badge', 'FOR PLAYERS'),
        'players_title': get_content('players_title', 'Benefits for Players'),
        'players_subtitle': get_content('players_subtitle', 'Everything you need to enjoy pickleball to the fullest'),
        'orgs_badge': get_content('orgs_badge', 'FOR ADMINISTRATORS'),
        'orgs_title': get_content('orgs_title', 'Benefits for Administrators'),
        'orgs_subtitle': get_content('orgs_subtitle', 'Powerful tools to manage courts, reservations, and tournaments'),
        'why_badge': get_content('why_badge', 'WHY PICKLESPHERE'),
        'why_title': get_content('why_title', 'Why Choose Our Platform?'),
        'why_subtitle': get_content('why_subtitle', 'We provide the best pickleball platform experience'),
        'gallery_badge': get_content('gallery_badge', 'GALLERY'),
        'gallery_title': get_content('gallery_title', 'Pickleball in Action'),
        'gallery_subtitle': get_content('gallery_subtitle', 'See what is happening across our courts and events'),
        'cta_title': get_content('cta_title', 'Join the PickleSphere Community'),
        'cta_subtitle': get_content('cta_subtitle', 'Whether you are a player looking for a court or an administrator managing the platform, PickleSphere is for you.'),
    }

    # Get dynamic stats

    # Auto-calculate years operating from 2024
    current_year = datetime.now().year
    years_operating = max(1, current_year - 2024 + 1)  # +1 to include 2024

    # Count actual completed tournaments
    tournaments_hosted = Tournament.objects.filter(status='completed').count()

    stats = {
        'total_courts': Court.objects.filter(is_active=True).count(),
        'total_members': User.objects.filter(is_active=True).count(),
        'years_operating': years_operating,
        'tournaments_hosted': tournaments_hosted
    }

    # Get gallery images from database
    gallery_images = AboutGalleryImage.objects.filter(is_active=True).order_by('display_order')

    # Calculate years experience for template
    current_year = datetime.now().year
    years_experience = max(1, current_year - 2024 + 1)

    return render(request, 'public/about.html', {
        'content': content,
        'stats': stats,
        'years_experience': years_experience,
        'gallery_images': gallery_images,
        'contact_info': contact_info,
    })


def contact_view(request):
    """Contact page - accessible to all users.
    NOT full-page cached because it contains a CSRF-protected POST form;
    its expensive content queries are cached at the data level instead and
    invalidated automatically when any contact CMS model changes."""

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if name and email and subject and message:
            # Save to database
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )

            # Send email using centralized email service
            send_contact_form_email({
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
            })
            messages.success(request, "Thank you for your message! We will get back to you soon.")
            return redirect("contact")
        else:
            messages.error(request, 'Please fill in all fields.')

    data = pages_cache_get_or_set('contact_page_data', _get_contact_page_data)
    return render(request, 'public/contact.html', data or {
        'content': {},
        'contact_info': {},
        'business_hours': [],
        'faqs': [],
        'social_links': [],
    })


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='privacy')
def privacy_policy_view(request):
    """Privacy Policy page - accessible to all users (cached for anonymous visitors)"""
    
    def get_content(section, default):
        content = PrivacyContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default
    
    sections = PrivacySection.objects.filter(is_active=True).order_by('section_number')
    
    context = {
        'hero_badge': get_content('hero_badge', 'Legal'),
        'hero_title': get_content('hero_title', 'Privacy Policy'),
        'hero_subtitle': get_content('hero_subtitle', ''),
        'last_updated_text': get_content('last_updated_text', 'Last Updated:'),
        'contact_email': get_content('contact_email', 'privacy@picklesphere.com'),
        'contact_phone': get_content('contact_phone', '09455470173'),
        'contact_address': get_content('contact_address', '123 Sports Complex Ave, Metro City'),
        'sections': sections,
    }
    return render(request, 'public/privacy_policy.html', context)


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='terms')
def terms_of_service_view(request):
    """Terms of Service page - accessible to all users (cached for anonymous visitors)"""
    
    def get_content(section, default):
        content = TermsContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default
    
    sections = TermsSection.objects.filter(is_active=True).order_by('section_number')
    
    context = {
        'hero_badge': get_content('hero_badge', 'Legal'),
        'hero_title': get_content('hero_title', 'Terms of Service'),
        'hero_subtitle': get_content('hero_subtitle', ''),
        'last_updated_text': get_content('last_updated_text', 'Last Updated:'),
        'contact_email': get_content('contact_email', 'legal@picklesphere.com'),
        'contact_phone': get_content('contact_phone', '09455470173'),
        'contact_address': get_content('contact_address', '123 Sports Complex Ave, Metro City'),
        'sections': sections,
    }
    return render(request, 'public/terms_of_service.html', context)


@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='faq')
def faq_view(request):
    """FAQ page - accessible to all users (cached for anonymous visitors)"""
    
    # Get CMS content sections with fallback defaults
    def get_content(section, default):
        content = FAQPageContent.objects.filter(section=section, is_active=True).first()
        return content.content if content else default
    
    cms_contents = {
        'hero_badge': get_content('hero_badge', 'Need Help?'),
        'hero_title': get_content('hero_title', 'Frequently Asked Questions'),
        'hero_subtitle': get_content('hero_subtitle', 'Find answers to common questions about PickleSphere, our platform, and services'),
        'search_placeholder': get_content('search_placeholder', 'Search for answers...'),
        'contact_title': get_content('contact_title', 'Still Need Help?'),
        'contact_text': get_content('contact_text', "Can't find what you're looking for? Our support team is here to help!"),
        'cta_button_text': get_content('cta_button_text', 'Contact Us'),
    }
    
    # Get categories and questions from database with fallback to defaults
    db_categories = FAQCategory.objects.prefetch_related('questions').filter(is_active=True).order_by('display_order')
    
    if db_categories.exists():
        faq_categories = []
        for cat in db_categories:
            questions = cat.questions.filter(is_active=True).order_by('display_order')
            if questions.exists():
                faq_categories.append({
                    'name': cat.name,
                    'icon': cat.icon,
                    'questions': [
                        {'question': q.question, 'answer': q.answer}
                        for q in questions
                    ]
                })
    
    if not db_categories.exists() or not faq_categories:
        # Fallback default FAQ categories
        faq_categories = [
            {
                'name': 'Reservations & Bookings',
                'icon': 'fa-calendar-check',
                'questions': [
                    {'question': 'How do I book a court?', 'answer': 'You can book a court by navigating to the "Find Courts" page, selecting your preferred court, date, and time slot.'},
                    {'question': 'Can I cancel or reschedule my reservation?', 'answer': 'Yes, you can cancel or reschedule your reservation up to 24 hours before your scheduled time.'},
                ]
            },
            {
                'name': 'Payments & Pricing',
                'icon': 'fa-money-bill-wave',
                'questions': [
                    {'question': 'What payment methods do you accept?', 'answer': 'We accept various payment methods including credit/debit cards, GCash, PayMaya, and bank transfers.'},
                    {'question': 'How do I get a refund?', 'answer': 'Refund requests can be submitted through the "Payment History" page. Refunds are processed within 5-7 business days.'},
                ]
            },
            {
                'name': 'Account & Technical',
                'icon': 'fa-user-circle',
                'questions': [
                    {'question': 'How do I reset my password?', 'answer': 'Click "Forgot Password" on the login page and enter your email address.'},
                    {'question': 'How do I contact customer support?', 'answer': f'You can reach us through the Contact page, email us at {STATIC_CONTACT_EMAIL}, or call us at {STATIC_CONTACT_PHONE}.'},
                ]
            },
        ]
    
    return render(request, 'public/faq.html', {
        'faq_categories': faq_categories,
        'cms_contents': cms_contents,
    })


# ============================================================================
# PRICING PAGE MANAGEMENT
# ============================================================================
