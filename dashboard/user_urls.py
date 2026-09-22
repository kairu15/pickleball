from django.urls import path
from . import views

urlpatterns = [
    # User Dashboard
    path('dashboard/', views.user_dashboard_view, name='user_dashboard'),
    path('messages/', views.user_messages_view, name='user_messages'),

    # Ratings
    path('ratings/submit/<int:reservation_id>/', views.submit_rating_view, name='submit_rating'),
    path('ratings/check/', views.check_pending_rating_view, name='check_pending_rating'),
]
