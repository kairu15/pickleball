from django.urls import path
from . import views

urlpatterns = [
    # Super Admin - Equipment CRUD
    path('equipment/', views.admin_equipment_list_view, name='super_admin_equipment_list'),
    path('equipment/create/', views.admin_equipment_create_view, name='super_admin_equipment_create'),
    path('equipment/<int:equipment_id>/edit/', views.admin_equipment_edit_view, name='super_admin_equipment_edit'),
    path('equipment/<int:equipment_id>/delete/', views.admin_equipment_delete_view, name='super_admin_equipment_delete'),
]
