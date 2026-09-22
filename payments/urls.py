from django.urls import path
from . import views

urlpatterns = [
    # Shared routes (used by multiple roles)
    path('proof/<int:payment_id>/', views.view_payment_proof_view, name='view_payment_proof'),
    path('proof-image/<int:payment_id>/', views.serve_payment_proof_image, name='serve_payment_proof_image'),
]
