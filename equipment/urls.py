from django.urls import path
from . import views

urlpatterns = [
    # Public Equipment Routes (for anonymous/browsing users)
    # Note: Logged-in users access equipment via /user/equipment/ with the same URL names
    path('', views.equipment_list_view, name='public_equipment_list'),
    path('<int:equipment_id>/', views.equipment_detail_view, name='public_equipment_detail'),
]
