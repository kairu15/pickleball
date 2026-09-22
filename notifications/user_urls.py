from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/<int:notification_id>/', views.notification_detail_view, name='notification_detail'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/<int:notification_id>/unread/', views.mark_notification_unread_view, name='mark_notification_unread'),
    path('notifications/mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification_view, name='delete_notification'),
    path('notifications/delete-selected/', views.delete_selected_notifications_view, name='delete_selected_notifications'),
    path('notifications/clear-all/', views.clear_all_notifications_view, name='clear_all_notifications'),
    path('notifications/<int:notification_id>/archive/', views.archive_notification_view, name='archive_notification'),
    path('notifications/<int:notification_id>/restore/', views.restore_notification_view, name='restore_notification'),
    path('notifications/preferences/', views.notification_preferences_view, name='notification_preferences'),
    path('notifications/api/unread-count/', views.get_unread_count_api, name='notification_unread_api'),
]
