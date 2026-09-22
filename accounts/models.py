from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('staff', 'Staff'),
        ('user', 'User'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    )
    
    SKILL_LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('pro', 'Pro'),
    )
    
    EMPLOYMENT_STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True, max_length=500, help_text='Tell others about yourself')
    birth_date = models.DateField(blank=True, null=True)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVEL_CHOICES, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Staff-specific fields
    staff_id = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text='Unique staff identifier')
    middle_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Middle Name')
    department = models.CharField(max_length=100, blank=True, null=True, help_text='Department or division')
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True, help_text='Internal notes about this staff member')
    
    # Map Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text='Latitude coordinate for map location')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text='Longitude coordinate for map location')
    
    # Social links
    website_url = models.URLField(blank=True, null=True, max_length=500)
    twitter_url = models.URLField(blank=True, null=True, max_length=500, verbose_name='X (Twitter) URL')
    instagram_url = models.URLField(blank=True, null=True, max_length=500)
    facebook_url = models.URLField(blank=True, null=True, max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_staff_member(self):
        """True for Staff role users (managed by the Super Admin)."""
        return self.role == 'staff'
    
    def is_normal_user(self):
        return self.role == 'user'
    
    def is_admin(self):
        """Checks if user is the Super Admin."""
        return self.role == 'super_admin'
    
    def is_staff_user(self):
        """Checks if user has staff-level access (Super Admin or Staff)."""
        return self.role in ['super_admin', 'staff']
    
    def sync_employment_status(self):
        """Sync employment_status with is_active to keep them consistent.
        Call this after setting is_active to ensure employment_status matches."""
        if self.is_active and self.employment_status in ('inactive', 'terminated'):
            self.employment_status = 'active'
        elif not self.is_active and self.employment_status == 'active':
            self.employment_status = 'inactive'
        return self
    
    def save(self, *args, **kwargs):
        """Override save to auto-sync employment_status with is_active."""
        self.sync_employment_status()
        super().save(*args, **kwargs)


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_activities'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.action}"


class StaffPermission(models.Model):
    """Granular permissions for staff members.
    Managed directly by the Super Admin."""
    MODULE_CHOICES = [
        ('manage_reservations', 'Manage Reservations'),
        ('manage_payments', 'Manage Payments'),
        ('manage_refunds', 'Manage Refunds'),
        ('manage_equipment', 'Manage Equipment'),
        ('manage_tournaments', 'Manage Tournaments'),
        ('manage_notifications', 'Manage Notifications'),
        ('view_reports', 'View Reports'),
        ('manage_courts', 'Manage Courts'),
        ('manage_sites', 'Manage Sites'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_permissions')
    manage_reservations = models.BooleanField(default=True)
    manage_payments = models.BooleanField(default=False)
    manage_refunds = models.BooleanField(default=False)
    manage_equipment = models.BooleanField(default=True)
    manage_tournaments = models.BooleanField(default=False)
    manage_notifications = models.BooleanField(default=True)
    view_reports = models.BooleanField(default=False)
    manage_courts = models.BooleanField(default=False)
    manage_sites = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_permissions'
        verbose_name = 'Staff Permission'
        verbose_name_plural = 'Staff Permissions'

    def get_enabled_count(self):
        """Return the number of enabled permissions."""
        count = 0
        for field_name, _ in self.MODULE_CHOICES:
            if getattr(self, field_name, False):
                count += 1
        return count

    def __str__(self):
        return f"Permissions for {self.user.username}"
