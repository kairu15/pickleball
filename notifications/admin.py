from django.contrib import admin
from .models import Notification, NotificationPreference, BroadcastMessage, NotificationTemplate, EmailLog, SmtpConfiguration, EmailOTP


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'category', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'category', 'priority', 'is_read', 'is_archived', 'is_deleted', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'read_at', 'archived_at']
    fieldsets = (
        ('User', {'fields': ['user']}),
        ('Content', {'fields': ['title', 'message']}),
        ('Classification', {'fields': ['notification_type', 'category', 'priority']}),
        ('Status', {'fields': ['is_read', 'is_archived', 'is_deleted', 'read_at', 'archived_at']}),
        ('Action', {'fields': ['action_url', 'action_text']}),
        ('Related Objects', {'fields': [
            'related_reservation', 'related_payment', 'related_match',
            'related_organization', 'related_tournament', 'related_equipment',
        ]}),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'frequency', 'email_notifications', 'push_notifications', 'updated_at']
    list_filter = ['frequency', 'email_notifications', 'push_notifications', 'sms_notifications']
    search_fields = ['user__username', 'user__email']


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'sent_by', 'sent_at', 'status', 'target_type', 'recipient_count', 'is_active']
    list_filter = ['status', 'target_type', 'priority', 'is_active', 'sent_at']
    search_fields = ['title', 'message', 'sent_by__username']
    date_hierarchy = 'sent_at'
    readonly_fields = ['sent_at', 'recipient_count', 'read_count', 'click_count']
    fieldsets = (
        ('Content', {'fields': ['title', 'message']}),
        ('Sender', {'fields': ['sent_by']}),
        ('Delivery', {'fields': ['target_type', 'target_roles', 'target_organization', 'target_users']}),
        ('Classification', {'fields': ['notification_type', 'category', 'priority']}),
        ('Status', {'fields': ['status', 'is_active', 'scheduled_for', 'sent_at']}),
        ('Statistics', {'fields': ['recipient_count', 'read_count', 'click_count']}),
    )


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'notification_type', 'priority', 'is_active']
    list_filter = ['category', 'notification_type', 'priority', 'is_active']
    search_fields = ['name', 'title_template', 'message_template']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'email_type', 'status', 'retry_count', 'created_at', 'sent_at']
    list_filter = ['status', 'email_type', 'created_at']
    search_fields = ['recipient', 'subject', 'email_type', 'error_message']
    date_hierarchy = 'created_at'
    readonly_fields = ['recipient', 'recipient_name', 'subject', 'body_preview', 'email_type',
                       'status', 'error_message', 'retry_count', 'max_retries',
                       'related_object_id', 'related_object_type', 'sent_by_user',
                       'created_at', 'sent_at']
    fieldsets = (
        ('Recipient', {'fields': ['recipient', 'recipient_name']}),
        ('Content', {'fields': ['subject', 'body_preview', 'email_type']}),
        ('Status', {'fields': ['status', 'error_message', 'retry_count', 'max_retries', 'created_at', 'sent_at']}),
        ('Related', {'fields': ['related_object_id', 'related_object_type', 'sent_by_user']}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SmtpConfiguration)
class SmtpConfigurationAdmin(admin.ModelAdmin):
    list_display = ['smtp_host', 'smtp_port', 'sender_email', 'status', 'encryption', 'is_active', 'updated_at']
    list_filter = ['status', 'encryption', 'is_active']
    search_fields = ['smtp_host', 'sender_email', 'smtp_username']
    readonly_fields = ['created_at', 'updated_at', 'updated_by']
    fieldsets = (
        ('SMTP Server', {'fields': ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'encryption']}),
        ('Sender', {'fields': ['sender_name', 'sender_email']}),
        ('Status', {'fields': ['status', 'is_active', 'created_at', 'updated_at', 'updated_by']}),
    )

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'purpose', 'is_used', 'attempts', 'max_attempts', 'created_at', 'expires_at', 'ip_address']
    list_filter = ['purpose', 'is_used', 'created_at', 'expires_at']
    search_fields = ['email', 'ip_address']
    date_hierarchy = 'created_at'
    readonly_fields = ['email', 'otp_hash', 'purpose', 'is_used', 'attempts', 'max_attempts',
                       'created_at', 'expires_at', 'used_at', 'ip_address', 'user']
    fieldsets = (
        ('User', {'fields': ['user', 'email']}),
        ('OTP', {'fields': ['otp_hash', 'purpose']}),
        ('Status', {'fields': ['is_used', 'attempts', 'max_attempts', 'created_at', 'expires_at', 'used_at']}),
        ('Metadata', {'fields': ['ip_address']}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
