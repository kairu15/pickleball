from django.urls import path
from . import views

urlpatterns = [
    # Super Admin - User Management
    path('users/', views.user_list_view, name='super_admin_user_list'),
    path('users/create/', views.user_create_view, name='super_admin_user_create'),
    path('users/edit/<int:user_id>/', views.user_edit_view, name='super_admin_user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='super_admin_user_delete'),
    path('activity-log/', views.user_activity_log, name='super_admin_activity_log'),
]
