from django.urls import path
from . import views

urlpatterns = [
    # Super Admin - Court Management
    path('courts/', views.admin_court_list_view, name='admin_court_list'),
    path('courts/create/', views.admin_court_create_view, name='admin_court_create'),
    path('courts/<int:court_id>/edit/', views.admin_court_edit_view, name='admin_court_edit'),
    path('courts/<int:court_id>/delete/', views.admin_court_delete_view, name='admin_court_delete'),

    # Super Admin - Site Management
    path('sites/', views.admin_site_list_view, name='admin_site_list'),
    path('sites/create/', views.admin_site_create_view, name='admin_site_create'),
    path('sites/<int:site_id>/edit/', views.admin_site_edit_view, name='admin_site_edit'),
    path('sites/<int:site_id>/delete/', views.admin_site_delete_view, name='admin_site_delete'),
]
