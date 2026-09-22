from django.urls import path
from . import views

urlpatterns = [
    # User - Payment Management
    # Old checkout flow (reservation already exists)
    path('checkout/<int:reservation_id>/', views.payment_checkout_view, name='payment_checkout'),
    # New checkout flow (session-based, deferred reservation)
    path('checkout/<uuid:checkout_token>/', views.checkout_page_view, name='checkout_page'),
    path('status/<int:payment_id>/', views.payment_status_view, name='payment_status'),
    path('history/', views.payment_history_view, name='payment_history'),
    path('receipt/<int:payment_id>/', views.payment_receipt_view, name='payment_receipt'),
    path('proof/<int:payment_id>/', views.view_payment_proof_view, name='view_payment_proof'),
    path('proof-image/<int:payment_id>/', views.serve_payment_proof_image, name='serve_payment_proof_image'),
]
