from django.urls import path
from . import views
from accounts import views as accounts_views

urlpatterns = [
    # Staff Dashboard
    path('', views.staff_dashboard_view, name='staff_dashboard'),
    path('profile/', accounts_views.profile_view, name='staff_profile'),
]
