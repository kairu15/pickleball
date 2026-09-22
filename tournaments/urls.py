from django.urls import path
from . import views

urlpatterns = [
    # Public / Player URLs
    path('', views.tournament_list, name='tournament_list'),
    path('<int:pk>/', views.tournament_detail, name='tournament_detail'),
    path('<int:pk>/register/', views.tournament_register, name='tournament_register'),

    # Admin / Staff URLs (kept here under tournaments/ for shared access)
    path('admin/', views.admin_tournament_list, name='admin_tournament_list'),
    path('admin/create/', views.admin_tournament_create, name='admin_tournament_create'),
    path('admin/<int:pk>/edit/', views.admin_tournament_edit, name='admin_tournament_edit'),
    path('admin/<int:pk>/manage/', views.admin_tournament_manage, name='admin_tournament_manage'),
    path('admin/<int:pk>/registrations/', views.admin_registration_list, name='admin_registration_list'),
    path('admin/<int:pk>/registrations/<int:reg_id>/review/', views.admin_registration_review, name='admin_registration_review'),
    path('admin/<int:pk>/registrations/bulk-approve/', views.admin_bulk_approve, name='admin_bulk_approve'),
    path('admin/<int:pk>/generate-matches/', views.admin_generate_matches, name='admin_generate_matches'),
    path('admin/<int:pk>/matches/', views.admin_match_list, name='admin_match_list'),
    path('admin/<int:pk>/matches/<int:match_id>/edit/', views.admin_match_edit, name='admin_match_edit'),
    path('admin/<int:pk>/schedule/', views.admin_schedule_matches, name='admin_schedule_matches'),
    path('admin/<int:pk>/leaderboard/', views.admin_leaderboard, name='admin_leaderboard'),
    path('admin/<int:pk>/teams/', views.admin_team_list, name='admin_team_list'),
    path('admin/<int:pk>/teams/create/', views.admin_team_create, name='admin_team_create'),
    path('admin/<int:pk>/bracket/', views.admin_tournament_bracket, name='admin_tournament_bracket'),
    path('admin/<int:pk>/change-status/', views.admin_change_status, name='admin_change_status'),

    # API
    path('api/match/<int:match_id>/update-score/', views.api_update_score, name='api_update_score'),
]
