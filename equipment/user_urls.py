from django.urls import path
from . import views

urlpatterns = [
    # User - Equipment
    path('equipment/', views.equipment_list_view, name='equipment_list'),
    path('equipment/<int:equipment_id>/', views.equipment_detail_view, name='equipment_detail'),
    path('equipment/rent/', views.equipment_rental_create_view, name='equipment_rental_create'),
    path('equipment/rental/<int:rental_id>/cancel/', views.cancel_equipment_rental_view, name='cancel_equipment_rental'),
]
