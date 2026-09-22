"""Unit tests for the accounts forms.

Registration and admin-managed user creation are the two places where a bug
either creates a user with a plaintext password or lets a duplicate identity
through, so both get explicit coverage here.
"""

from django.test import TestCase

from accounts.forms import (
    AdminUserCreateForm,
    AdminUserUpdateForm,
    PasswordResetRequestForm,
    UserProfileForm,
    UserRegistrationForm,
)
from accounts.models import User

# Passes all four configured AUTH_PASSWORD_VALIDATORS (length, common, numeric,
# similarity) so a test only fails for the reason it is actually about.
VALID_PASSWORD = 'Str0ng-Pickle-Pass!'


def registration_payload(**overrides):
    payload = {
        'username': 'newplayer',
        'first_name': 'Nina',
        'last_name': 'Reyes',
        'email': 'nina@example.com',
        'phone_number': '+63 912 345 6789',
        'password1': VALID_PASSWORD,
        'password2': VALID_PASSWORD,
        'agree_terms': 'on',
    }
    payload.update(overrides)
    return payload


class UserRegistrationFormTests(TestCase):
    def test_valid_payload_creates_a_regular_user_with_a_hashed_password(self):
        form = UserRegistrationForm(data=registration_payload())
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertEqual(user.role, 'user')
        self.assertEqual(user.email, 'nina@example.com')
        self.assertNotEqual(user.password, VALID_PASSWORD)
        self.assertTrue(user.check_password(VALID_PASSWORD))

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username='existing', email='NINA@example.com', password=VALID_PASSWORD,
        )

        form = UserRegistrationForm(data=registration_payload())

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_username_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username='NewPlayer', email='other@example.com', password=VALID_PASSWORD,
        )

        form = UserRegistrationForm(data=registration_payload())

        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_mismatched_passwords_are_rejected(self):
        form = UserRegistrationForm(
            data=registration_payload(password2='Str0ng-Pickle-Pass?-mismatch'),
        )

        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_terms_acceptance_is_required(self):
        payload = registration_payload()
        payload.pop('agree_terms')

        form = UserRegistrationForm(data=payload)

        self.assertFalse(form.is_valid())
        self.assertIn('agree_terms', form.errors)


class AdminUserCreateFormTests(TestCase):
    def test_password_mismatch_is_a_form_error_and_not_a_crash(self):
        form = AdminUserCreateForm(data={
            'username': 'staff10',
            'first_name': 'Sam',
            'last_name': 'Cruz',
            'email': 'sam@example.com',
            'role': 'staff',
            'is_active': 'on',
            'password1': VALID_PASSWORD,
            'password2': 'Something-Else-123!',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Passwords do not match.', form.non_field_errors())

    def test_save_stores_the_password_hashed(self):
        form = AdminUserCreateForm(data={
            'username': 'staff11',
            'first_name': 'Sam',
            'last_name': 'Cruz',
            'email': 'sam2@example.com',
            'role': 'staff',
            'is_active': 'on',
            'password1': VALID_PASSWORD,
            'password2': VALID_PASSWORD,
        })
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertEqual(user.role, 'staff')
        self.assertTrue(user.check_password(VALID_PASSWORD))

    def test_save_with_commit_false_does_not_touch_the_database(self):
        form = AdminUserCreateForm(data={
            'username': 'staff12',
            'first_name': 'Sam',
            'last_name': 'Cruz',
            'email': 'sam3@example.com',
            'role': 'staff',
            'is_active': 'on',
            'password1': VALID_PASSWORD,
            'password2': VALID_PASSWORD,
        })
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save(commit=False)

        self.assertIsNone(user.pk)
        self.assertEqual(User.objects.filter(username='staff12').count(), 0)


class AdminUserUpdateFormTests(TestCase):
    def test_role_and_active_flag_can_be_changed(self):
        user = User.objects.create_user(
            username='staff13', password=VALID_PASSWORD, role='staff',
        )
        form = AdminUserUpdateForm(data={
            'first_name': 'Sam',
            'last_name': 'Cruz',
            'email': 'sam4@example.com',
            'phone_number': '',
            'role': 'super_admin',
            'is_active': 'on',
        }, instance=user)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        user.refresh_from_db()
        self.assertEqual(user.role, 'super_admin')


class PasswordResetRequestFormTests(TestCase):
    def test_unknown_email_gets_the_generic_message(self):
        # The form deliberately refuses unknown addresses so the reset view
        # cannot be used to enumerate registered accounts.
        form = PasswordResetRequestForm(data={'email': 'nobody@example.com'})

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_known_email_passes_validation(self):
        User.objects.create_user(
            username='known', email='known@example.com', password=VALID_PASSWORD,
        )

        form = PasswordResetRequestForm(data={'email': 'known@example.com'})

        self.assertTrue(form.is_valid(), form.errors)


class UserProfileFormTests(TestCase):
    def test_profile_fields_are_persisted(self):
        user = User.objects.create_user(username='player10', password=VALID_PASSWORD)
        form = UserProfileForm(data={
            'first_name': 'Pat',
            'last_name': 'Lopez',
            'email': 'pat@example.com',
            'gender': 'O',
            'phone_number': '+63 900 000 0000',
            'address': '123 Court St',
            'bio': 'Weekend player',
            'birth_date': '1995-04-01',
            'skill_level': 'intermediate',
            'latitude': '',
            'longitude': '',
            'website_url': '',
            'twitter_url': '',
            'instagram_url': '',
            'facebook_url': '',
        }, instance=user)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Pat')
        self.assertEqual(user.skill_level, 'intermediate')
        self.assertEqual(user.address, '123 Court St')
