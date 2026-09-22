from django.urls import path
from . import views

urlpatterns = [
    # Staff - Equipment Management
    path('equipment/', views.staff_equipment_view, name='staff_equipment'),
    path('equipment/checkout/<int:rental_id>/', views.check_out_equipment_view, name='staff_equipment_checkout'),
    path('equipment/checkin/<int:rental_id>/', views.check_in_equipment_view, name='staff_equipment_checkin'),
]
