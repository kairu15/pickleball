from django.urls import path
from . import views

urlpatterns = [
    path('smtp-settings/', views.smtp_settings_view, name='super_admin_smtp_settings'),
    path('smtp-settings/test/', views.smtp_test_email_view, name='super_admin_smtp_test'),
    path('email-logs/', views.email_log_list_view, name='super_admin_email_logs'),
    path('email-logs/<int:log_id>/', views.email_log_detail_view, name='super_admin_email_log_detail'),
    path('notifications/', views.notification_list_view, name='super_admin_notification_list'),
    path('notifications/<int:notification_id>/', views.notification_detail_view, name='super_admin_notification_detail'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='super_admin_mark_notification_read'),
    path('notifications/<int:notification_id>/unread/', views.mark_notification_unread_view, name='super_admin_mark_notification_unread'),
    path('notifications/mark-all-read/', views.mark_all_read_view, name='super_admin_mark_all_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification_view, name='super_admin_delete_notification'),
    path('notifications/delete-selected/', views.delete_selected_notifications_view, name='super_admin_delete_selected_notifications'),
    path('notifications/clear-all/', views.clear_all_notifications_view, name='super_admin_clear_all_notifications'),
    path('notifications/<int:notification_id>/archive/', views.archive_notification_view, name='super_admin_archive_notification'),
    path('notifications/<int:notification_id>/restore/', views.restore_notification_view, name='super_admin_restore_notification'),
    path('notifications/preferences/', views.notification_preferences_view, name='super_admin_notification_preferences'),
    path('notifications/api/unread-count/', views.get_unread_count_api, name='super_admin_notification_unread_api'),
]
