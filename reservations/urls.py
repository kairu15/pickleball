from django.urls import path
from . import views

urlpatterns = [
    # Public API Routes (shared across roles)
    path('api/time-slots/', views.get_time_slots_api, name='get_time_slots'),
    path('api/monthly-availability/', views.get_monthly_availability_api, name='get_monthly_availability'),
    path('api/verify-slot/', views.verify_slot_api, name='verify_slot'),
]
