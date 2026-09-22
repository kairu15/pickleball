from django.urls import path
from . import views

urlpatterns = [
    # Super Admin - Reservation Management
    path('reservations/', views.admin_reservation_list_view, name='super_admin_reservation_list'),
    path('reservations/create/', views.admin_reservation_create_view, name='super_admin_reservation_create'),
    path('reservations/<int:reservation_id>/edit/', views.admin_reservation_edit_view, name='super_admin_reservation_edit'),
    path('reservations/<int:reservation_id>/delete/', views.admin_reservation_delete_view, name='super_admin_reservation_delete'),
]
