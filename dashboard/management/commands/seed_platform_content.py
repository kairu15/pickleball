"""
Management command to seed HomePageContent, AboutContent, and ContactContent
with platform-focused messaging for PickleSphere.
Run with: python manage.py seed_platform_content
"""
from django.core.management.base import BaseCommand
from dashboard.models import (
    HomePageContent, AboutContent, ContactContent, ContactInfo
)


class Command(BaseCommand):
    help = 'Seed HomePageContent, AboutContent, and ContactContent with platform-focused messaging'

    def handle(self, *args, **options):
        # ===============================================================
        # 1. HOMEPAGE CONTENT
        # ===============================================================
        self.stdout.write("Updating HomePageContent records...")

        homepage_defaults = {
            'hero_title': 'Welcome to PickleSphere',
            'hero_subtitle': (
                'The all-in-one platform connecting pickleball players with courts, '
                'tournaments, and equipment nationwide. Find, book, and play '
                'all in one place.'
            ),
            'about_title': 'Your Pickleball Journey Starts Here',
            'about_text': (
                'PickleSphere is a comprehensive platform that connects pickleball '
                'enthusiasts with courts, equipment, and tournaments across the '
                'country. Whether you are a beginner looking to learn or a seasoned '
                'pro seeking competition, we make it easy to find, book, and play.'
            ),
            'cta_title': 'Ready to Play?',
            'cta_text': (
                'Join thousands of pickleball players. Find courts, join tournaments, '
                'and be part of the community!'
            ),
        }

        created = updated = 0
        for section, content_text in homepage_defaults.items():
            obj, was_created = HomePageContent.objects.update_or_create(
                section=section,
                defaults={'content': content_text, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"  HomePageContent: {created} created, {updated} updated"
        ))

        # ===============================================================
        # 2. ABOUT PAGE CONTENT
        # ===============================================================
        self.stdout.write("Updating AboutContent records...")

        about_defaults = {
            'hero_badge': 'About the Platform',
            'hero_title': 'About PickleSphere',
            'hero_subtitle': (
                "The Philippines' premier pickleball platform, connecting players "
                "with courts, tournaments, and equipment nationwide."
            ),
            'mission_title': 'Our Mission',
            'mission_text': (
                'To grow the sport of pickleball by providing a centralized platform '
                'that connects players with courts, simplifies court '
                'reservations, streamlines tournament management, and fosters a '
                'vibrant, inclusive pickleball community across the Philippines.'
            ),
            'mission_features': (
                'Connect players to courts,Simplify court reservations,'
                'Streamline tournaments,Build community'
            ),
            'vision_title': 'Our Vision',
            'vision_text': (
                'To become the leading pickleball ecosystem in Southeast Asia, where '
                'every player can easily find a court, join a tournament, and be part '
                'of a thriving community.'
            ),
            'vision_features': (
                'Leading ecosystem,Accessible to all,Empower players,Grow the sport'
            ),
            'stats_courts': 'Courts on Platform',
            'stats_members': 'Active Players',
            'stats_years': 'Years in Operation',
            'stats_tournaments': 'Tournaments Hosted',
            'offers_badge': 'WHAT WE OFFER',
            'offers_title': 'Platform Features',
            'offers_subtitle': 'Everything you need for the perfect pickleball experience',
            'howitworks_badge': 'HOW IT WORKS',
            'howitworks_title': 'Getting Started is Easy',
            'howitworks_subtitle': 'Follow these simple steps to start playing',
            'players_badge': 'FOR PLAYERS',
            'players_title': 'Benefits for Players',
            'players_subtitle': 'Everything you need to enjoy pickleball to the fullest',
            'orgs_badge': 'FOR ADMINISTRATORS',
            'orgs_title': 'Benefits for Administrators',
            'orgs_subtitle': 'Powerful tools to manage courts, reservations, and tournaments',
            'why_badge': 'WHY PICKLESPHERE',
            'why_title': 'Why Choose Our Platform?',
            'why_subtitle': 'We provide the best pickleball platform experience',
            'gallery_badge': 'GALLERY',
            'gallery_title': 'Pickleball in Action',
            'gallery_subtitle': 'See what is happening across our courts and events',
            'cta_title': 'Join the PickleSphere Community',
            'cta_subtitle': (
                'Whether you are a player looking for a court or an administrator '
                'managing the platform, PickleSphere is for you.'
            ),
        }

        created = updated = 0
        for section, content_text in about_defaults.items():
            obj, was_created = AboutContent.objects.update_or_create(
                section=section,
                defaults={'content': content_text, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"  AboutContent: {created} created, {updated} updated"
        ))

        # ===============================================================
        # 3. CONTACT PAGE CONTENT
        # ===============================================================
        self.stdout.write("Updating ContactContent records...")

        contact_defaults = {
            'hero_badge': 'Platform Support',
            'hero_title': 'Get in Touch',
            'hero_subtitle': (
                'Have a question, suggestion, or need help? '
                'Our support team is here to assist you.'
            ),
            'phone_label': 'Call Us',
            'phone_hours': 'Mon-Sat, 9AM - 6PM',
            'email_label': 'Email Us',
            'email_response': 'We reply within 24 hours',
            'visit_label': 'Our Office',
            'visit_city': '',
            'form_title': 'Send us a Message',
            'form_name_label': 'Your Name',
            'form_email_label': 'Email Address',
            'form_subject_label': 'Subject',
            'form_message_label': 'Message',
            'form_submit_text': 'Send Message',
            'hours_title': 'Platform Support Hours',
            'quick_links_title': 'Quick Links',
            'social_title': 'Follow Us',
            'faq_badge': 'FAQ',
            'faq_title': 'Frequently Asked Questions',
            'faq_subtitle': 'Quick answers to common questions about our platform',
            'cta_title': 'Ready to Play?',
            'cta_subtitle': (
                'Join thousands of players enjoying pickleball through our platform. '
                'Find courts, join tournaments, and be part of the community!'
            ),
        }

        created = updated = 0
        for section, content_text in contact_defaults.items():
            obj, was_created = ContactContent.objects.update_or_create(
                section=section,
                defaults={'content': content_text, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"  ContactContent: {created} created, {updated} updated"
        ))

        # ===============================================================
        # 4. CONTACT INFO (singleton)
        # ===============================================================
        self.stdout.write("Updating ContactInfo record...")

        ContactInfo.objects.update_or_create(
            pk=1,
            defaults={
                'phone': '09455470173',
                'email': 'picklesphere@gmail.com',
                'address': 'PickleSphere Headquarters',
                'city_country': 'Philippines',
                'is_active': True,
            },
        )
        self.stdout.write(self.style.SUCCESS("  ContactInfo: updated"))

        self.stdout.write(self.style.SUCCESS(
            "\nAll content records seeded successfully!"
        ))
