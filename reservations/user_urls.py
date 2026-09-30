from django.urls import path
from . import views

urlpatterns = [
    # User - Reservation Management
    path('reservations/', views.reservation_list_view, name='reservation_list'),
    path('reservations/create/', views.reservation_create_view, name='reservation_create'),
    path('reservations/calendar/', views.calendar_view, name='calendar'),
    path('reservations/<int:reservation_id>/', views.reservation_detail_view, name='reservation_detail'),
    path('reservations/<int:reservation_id>/edit/', views.reservation_edit_view, name='reservation_edit'),
    path('reservations/<int:reservation_id>/cancel/', views.cancel_reservation_view, name='cancel_reservation'),

    # User - Waitlist
    path('waitlist/', views.waitlist_list_view, name='waitlist_list'),
    path('courts/<int:court_id>/waitlist/join/', views.waitlist_join_view, name='waitlist_join'),
    path('waitlist/<int:entry_id>/leave/', views.waitlist_leave_view, name='waitlist_leave'),
]
