from django.urls import path
from . import views

urlpatterns = [
    # Public Court Routes
    path('', views.court_list_view, name='court_list'),
    path('<int:court_id>/', views.court_detail_view, name='court_detail'),
    path('<int:court_id>/directions/', views.court_directions_view, name='court_directions'),
    path('<int:court_id>/availability/', views.court_availability_view, name='court_availability'),
    path('<int:court_id>/api/slots/', views.court_slots_api, name='court_slots_api'),
    path('<int:court_id>/favorite/', views.toggle_favorite_view, name='toggle_favorite'),
]
