from django.urls import path
from . import views

urlpatterns = [
    # Public Pages
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('all_courts/', views.all_courts_view, name='all_courts'),
    path('court/<int:court_id>/', views.court_view_view, name='court_view'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),
    path('faq/', views.faq_view, name='faq'),
]
