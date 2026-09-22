"""Unit tests for the accounts models.

The role helper methods (``is_admin`` / ``is_staff_user`` / ...) are what every
access-control decorator in the project calls, so a regression here silently
opens or closes whole areas of the app. These tests pin that behaviour.
"""

from django.test import TestCase

from accounts.models import StaffPermission, User, UserActivity


class UserRoleHelperTests(TestCase):
    def test_super_admin_role_helpers(self):
        user = User.objects.create_user(
            username='admin1', password='Str0ng-Pickle-Pass!', role='super_admin',
        )

        self.assertTrue(user.is_admin())
        self.assertTrue(user.is_super_admin())
        self.assertTrue(user.is_staff_user())
        self.assertFalse(user.is_staff_member())
        self.assertFalse(user.is_normal_user())

    def test_staff_role_helpers(self):
        user = User.objects.create_user(
            username='staff1', password='Str0ng-Pickle-Pass!', role='staff',
        )

        self.assertFalse(user.is_admin())
        self.assertFalse(user.is_super_admin())
        self.assertTrue(user.is_staff_user())
        self.assertTrue(user.is_staff_member())
        self.assertFalse(user.is_normal_user())

    def test_regular_user_is_the_default_role(self):
        user = User.objects.create_user(username='player1', password='Str0ng-Pickle-Pass!')

        self.assertEqual(user.role, 'user')
        self.assertTrue(user.is_normal_user())
        self.assertFalse(user.is_staff_user())

    def test_str_includes_role_display(self):
        user = User.objects.create_user(
            username='player2', password='Str0ng-Pickle-Pass!', role='user',
        )

        self.assertEqual(str(user), 'player2 (User)')


class EmploymentStatusSyncTests(TestCase):
    """``employment_status`` is derived from ``is_active`` on every save.

    Staff management screens set ``is_active`` only, so the sync on save is what
    keeps the two fields from drifting apart.
    """

    def test_inactive_user_is_marked_inactive_on_save(self):
        user = User.objects.create_user(
            username='staff2', password='Str0ng-Pickle-Pass!', role='staff', is_active=False,
        )

        self.assertEqual(user.employment_status, 'inactive')

    def test_reactivated_user_returns_to_active(self):
        user = User.objects.create_user(
            username='staff3', password='Str0ng-Pickle-Pass!', role='staff', is_active=False,
        )
        self.assertEqual(user.employment_status, 'inactive')

        user.is_active = True
        user.save()

        self.assertEqual(user.employment_status, 'active')

    def test_suspended_status_is_preserved_for_inactive_user(self):
        # 'suspended' is a decision made by an admin, not a derived state, so
        # re-saving an inactive suspended user must not overwrite it.
        user = User.objects.create_user(
            username='staff4', password='Str0ng-Pickle-Pass!', role='staff', is_active=False,
        )
        user.employment_status = 'suspended'
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.employment_status, 'suspended')

    def test_sync_employment_status_returns_self_for_chaining(self):
        user = User(username='staff5', role='staff')
        self.assertIs(user.sync_employment_status(), user)


class StaffPermissionTests(TestCase):
    def test_default_permission_count(self):
        user = User.objects.create_user(
            username='staff6', password='Str0ng-Pickle-Pass!', role='staff',
        )
        permissions = StaffPermission.objects.create(user=user)

        # manage_reservations, manage_equipment and manage_notifications default on.
        self.assertEqual(permissions.get_enabled_count(), 3)

    def test_disabling_every_module_reports_zero(self):
        user = User.objects.create_user(
            username='staff7', password='Str0ng-Pickle-Pass!', role='staff',
        )
        permissions = StaffPermission.objects.create(user=user)
        for field_name, _ in StaffPermission.MODULE_CHOICES:
            setattr(permissions, field_name, False)
        permissions.save()

        self.assertEqual(permissions.get_enabled_count(), 0)

    def test_every_module_choice_is_a_real_field(self):
        # Guards against a MODULE_CHOICES entry without a matching BooleanField,
        # which would make get_enabled_count() quietly under-count.
        permissions = StaffPermission()
        for field_name, _ in StaffPermission.MODULE_CHOICES:
            self.assertTrue(
                hasattr(permissions, field_name),
                f'StaffPermission.MODULE_CHOICES lists {field_name} but the model has no such field',
            )


class UserActivityTests(TestCase):
    def test_str_labels_the_activity_owner_and_action(self):
        user = User.objects.create_user(username='player3', password='Str0ng-Pickle-Pass!')
        activity = UserActivity.objects.create(user=user, action='Logged in')

        self.assertEqual(str(activity), 'player3 - Logged in')
