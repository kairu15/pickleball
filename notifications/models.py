from django.db import models
from django.utils import timezone
from django.conf import settings


class EmailLog(models.Model):
    """
    Tracks all sent emails for auditing and debugging.
    """
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    )

    recipient = models.EmailField()
    recipient_name = models.CharField(max_length=255, blank=True, default='')
    subject = models.CharField(max_length=500)
    body_preview = models.TextField(blank=True, help_text='Plain text preview of email body')
    email_type = models.CharField(max_length=100, blank=True, default='', help_text='e.g. welcome, password_reset, reservation_confirmed')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    related_object_id = models.CharField(max_length=50, blank=True, null=True, help_text='ID of related model (e.g. reservation ID)')
    related_object_type = models.CharField(max_length=50, blank=True, null=True, help_text='Model name (e.g. Reservation, Payment)')
    sent_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, help_text='User who triggered this email'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email_type', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"[{self.get_status_display()}] {self.email_type} -> {self.recipient}: {self.subject[:50]}"

    def mark_sent(self):
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_failed(self, error_message=''):
        self.status = 'failed'
        self.error_message = str(error_message)[:1000]
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count'])


class SmtpConfiguration(models.Model):
    """
    Stores SMTP configuration for sending emails.
    Only the super admin can manage these settings.
    """
    ENABLE_CHOICES = (
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
    )
    ENCRYPTION_CHOICES = (
        ('tls', 'TLS'),
        ('ssl', 'SSL'),
        ('none', 'None'),
    )

    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com')
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.EmailField(max_length=255, default='', blank=True)
    smtp_password = models.CharField(max_length=500, default='', blank=True, help_text='SMTP password or app password')
    encryption = models.CharField(max_length=10, choices=ENCRYPTION_CHOICES, default='tls')
    sender_name = models.CharField(max_length=255, default='PickleSphere')
    sender_email = models.EmailField(max_length=255, default='noreply@picklesphere.com')
    status = models.CharField(max_length=10, choices=ENABLE_CHOICES, default='enabled')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'smtp_configurations'
        verbose_name = 'SMTP Configuration'
        verbose_name_plural = 'SMTP Configurations'

    def __str__(self):
        return f"SMTP: {self.smtp_host}:{self.smtp_port} ({self.get_status_display()})"

    def is_enabled(self):
        return self.status == 'enabled' and self.is_active

    def get_encryption_settings(self):
        if self.encryption == 'tls':
            return {'use_tls': True, 'use_ssl': False}
        elif self.encryption == 'ssl':
            return {'use_tls': False, 'use_ssl': True}
        else:
            return {'use_tls': False, 'use_ssl': False}

    def get_sender_display(self):
        if self.sender_name:
            return f'{self.sender_name} <{self.sender_email}>'
        return self.sender_email


class EmailOTP(models.Model):
    """
    Stores One-Time Passwords for email verification (registration & password reset).
    OTPs are hashed before storage for security.
    """
    PURPOSE_CHOICES = (
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, help_text='User (may be null during registration before user is fully created)'
    )
    email = models.EmailField()
    otp_hash = models.CharField(max_length=128, help_text='SHA-256 hash of the OTP code')
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0, help_text='Number of verification attempts')
    max_attempts = models.IntegerField(default=5, help_text='Max failed attempts before OTP is invalidated')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'email_otps'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'purpose', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'

    def __str__(self):
        return f"OTP for {self.email} ({self.get_purpose_display()})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < self.max_attempts

    def verify_otp(self, otp_code):
        """Verify the given OTP code against the stored hash."""
        import hashlib
        self.attempts += 1
        if self.attempts >= self.max_attempts:
            self.save(update_fields=['attempts'])
            return False
        
        hashed = hashlib.sha256(otp_code.encode()).hexdigest()
        if hashed == self.otp_hash and self.is_valid:
            self.is_used = True
            self.used_at = timezone.now()
            self.save(update_fields=['is_used', 'used_at', 'attempts'])
            return True
        
        self.save(update_fields=['attempts'])
        return False


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )

    CATEGORY_CHOICES = (
        ('reservation', 'Reservations'),
        ('payment', 'Payments'),
        ('refund', 'Refunds'),
        ('cancellation', 'Cancellations'),
        ('tournament', 'Tournaments'),
        ('equipment', 'Equipment'),
        ('staff', 'Staff'),
        ('user', 'Users'),
        ('report', 'Reports'),
        ('system', 'System'),
        ('security', 'Security'),
        ('maintenance', 'Maintenance'),
        ('announcement', 'Announcements'),
        ('promotion', 'Promotions'),
        ('message', 'Messages'),
        ('account', 'Account'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200, blank=True, default='')
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default='info'
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='system'
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal'
    )
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    action_url = models.CharField(max_length=500, blank=True, help_text='URL to redirect when clicked')
    action_text = models.CharField(max_length=100, blank=True, default='View Details')

    related_reservation = models.ForeignKey(
        'reservations.Reservation', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    related_payment = models.ForeignKey(
        'payments.Payment', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    related_match = models.ForeignKey(
        'scoring.Match', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    related_tournament = models.ForeignKey(
        'tournaments.Tournament', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    related_equipment = models.ForeignKey(
        'equipment.Equipment', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'category', '-created_at']),
            models.Index(fields=['user', 'priority', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.user.username}: {self.title or self.message[:50]}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])

    def archive(self):
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=['is_archived', 'archived_at'])

    def restore(self):
        self.is_archived = False
        self.archived_at = None
        self.save(update_fields=['is_archived', 'archived_at'])

    @property
    def icon_class(self):
        icons = {
            'reservation': 'fa-calendar-check',
            'payment': 'fa-credit-card',
            'refund': 'fa-undo-alt',
            'cancellation': 'fa-times-circle',
            'tournament': 'fa-trophy',
            'equipment': 'fa-tools',
            'staff': 'fa-users-gear',
            'user': 'fa-user',
            'report': 'fa-chart-bar',
            'system': 'fa-cog',
            'security': 'fa-shield-alt',
            'maintenance': 'fa-wrench',
            'announcement': 'fa-bullhorn',
            'promotion': 'fa-tags',
            'message': 'fa-envelope',
            'account': 'fa-user-circle',
        }
        return icons.get(self.category, 'fa-bell')

    @property
    def category_color(self):
        colors = {
            'reservation': '#3B7A8C',
            'payment': '#28a745',
            'refund': '#fd7e14',
            'cancellation': '#dc3545',
            'tournament': '#ffc107',
            'equipment': '#6f42c1',
            'staff': '#e83e8c',
            'user': '#17a2b8',
            'report': '#6c757d',
            'system': '#343a40',
            'security': '#dc3545',
            'maintenance': '#ffc107',
            'announcement': '#0d6efd',
            'promotion': '#fd7e14',
            'message': '#e83e8c',
            'account': '#17a2b8',
        }
        return colors.get(self.category, '#6c757d')

    @property
    def type_color(self):
        type_colors = {
            'info': '#17a2b8',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
        }
        return type_colors.get(self.notification_type, '#6c757d')

    @property
    def time_display(self):
        now = timezone.now()
        diff = now - self.created_at
        if diff.days == 0:
            if diff.seconds < 60:
                return 'Just now'
            elif diff.seconds < 3600:
                return f'{diff.seconds // 60}m ago'
            else:
                return f'{diff.seconds // 3600}h ago'
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return f'{diff.days}d ago'
        elif diff.days < 30:
            return f'{diff.days // 7}w ago'
        elif diff.days < 365:
            return f'{diff.days // 30}mo ago'
        else:
            return f'{diff.days // 365}y ago'

    @property
    def group_key(self):
        now = timezone.now()
        if self.created_at.date() == now.date():
            return 'Today'
        elif self.created_at.date() == (now - timezone.timedelta(days=1)).date():
            return 'Yesterday'
        elif self.created_at.date() >= (now - timezone.timedelta(days=7)).date():
            return 'This Week'
        else:
            return 'Earlier'


class NotificationPreference(models.Model):
    FREQUENCY_CHOICES = (
        ('instant', 'Instant'),
        ('hourly', 'Hourly Digest'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    notify_reservation = models.BooleanField(default=True)
    notify_payment = models.BooleanField(default=True)
    notify_refund = models.BooleanField(default=True)
    notify_cancellation = models.BooleanField(default=True)
    notify_tournament = models.BooleanField(default=True)
    notify_equipment = models.BooleanField(default=True)
    notify_staff = models.BooleanField(default=True)
    notify_user = models.BooleanField(default=True)
    notify_report = models.BooleanField(default=False)
    notify_system = models.BooleanField(default=True)
    notify_security = models.BooleanField(default=True)
    notify_maintenance = models.BooleanField(default=True)
    notify_announcement = models.BooleanField(default=True)
    notify_promotion = models.BooleanField(default=False)
    notify_message = models.BooleanField(default=True)
    notify_account = models.BooleanField(default=True)

    email_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=False)
    sms_notifications = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=True)

    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default='instant'
    )

    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f'Preferences for {self.user.username}'

    def is_category_enabled(self, category):
        field_map = {
            'reservation': 'notify_reservation',
            'payment': 'notify_payment',
            'refund': 'notify_refund',
            'cancellation': 'notify_cancellation',
            'tournament': 'notify_tournament',
            'equipment': 'notify_equipment',
            'staff': 'notify_staff',
            'user': 'notify_user',
            'report': 'notify_report',
            'system': 'notify_system',
            'security': 'notify_security',
            'maintenance': 'notify_maintenance',
            'announcement': 'notify_announcement',
            'promotion': 'notify_promotion',
            'message': 'notify_message',
            'account': 'notify_account',
        }
        field = field_map.get(category)
        if field:
            return getattr(self, field, True)
        return True


class BroadcastMessage(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('scheduled', 'Scheduled'),
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='broadcasts'
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)

    target_roles = models.JSONField(default=list, blank=True)
    target_type = models.CharField(
        max_length=20,
        choices=[
            ('all', 'All Users'),
            ('roles', 'Specific Roles'),
            ('users', 'Specific Users'),
        ],
        default='all'
    )
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='targeted_broadcasts'
    )

    notification_type = models.CharField(
        max_length=20, choices=Notification.NOTIFICATION_TYPES, default='info'
    )
    category = models.CharField(
        max_length=20, choices=Notification.CATEGORY_CHOICES, default='announcement'
    )
    priority = models.CharField(
        max_length=10, choices=Notification.PRIORITY_CHOICES, default='normal'
    )

    recipient_count = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'broadcast_messages'
        ordering = ['-sent_at']

    def __str__(self):
        return f'Broadcast: {self.title}'


class NotificationTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(
        max_length=200,
        help_text='Use {variable} placeholders'
    )
    message_template = models.TextField(
        help_text='Use {variable} placeholders for dynamic content'
    )
    notification_type = models.CharField(
        max_length=20, choices=Notification.NOTIFICATION_TYPES, default='info'
    )
    category = models.CharField(
        max_length=20, choices=Notification.CATEGORY_CHOICES, default='system'
    )
    priority = models.CharField(
        max_length=10, choices=Notification.PRIORITY_CHOICES, default='normal'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_templates'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'

    def __str__(self):
        return self.name

    def render_title(self, **kwargs):
        return self.title_template.format(**kwargs)

    def render_message(self, **kwargs):
        return self.message_template.format(**kwargs)
