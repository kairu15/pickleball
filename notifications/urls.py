from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('broadcast/', views.broadcast_create_view, name='super_admin_broadcast_create'),
    path('broadcast/list/', views.broadcast_list_view, name='super_admin_broadcast_list'),
    path('broadcast/<int:broadcast_id>/', views.broadcast_detail_view, name='super_admin_broadcast_detail'),
    path('broadcast/stats/', views.get_broadcast_stats_api, name='super_admin_broadcast_stats'),
    # SMTP settings and email logs are in admin_urls.py
]
