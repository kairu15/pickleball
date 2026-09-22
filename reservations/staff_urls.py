from django.urls import path
from . import views

urlpatterns = [
    # Staff - Reservation Management
    path('reservations/', views.staff_reservations_view, name='staff_reservations'),
    path('reservations/<int:reservation_id>/approve/', views.approve_reservation_view, name='staff_approve_reservation'),
    path('cancellations/', views.staff_cancellations_view, name='staff_cancellations'),
    path('refunds/', views.staff_refund_processing_view, name='staff_refund_processing'),
    path('refunds/history/', views.staff_refund_history_view, name='staff_refund_history'),
]
