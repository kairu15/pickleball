from django.urls import path
from . import views

urlpatterns = [
    # User - Tournament Management
    path('tournaments/', views.my_tournaments, name='my_tournaments'),
    path('tournaments/matches/', views.my_matches, name='my_matches'),
    path('tournaments/<int:pk>/register/', views.tournament_register, name='tournament_register'),
    path('tournaments/<int:pk>/', views.tournament_detail, name='tournament_detail'),
]
