from django.urls import path
from . import views

urlpatterns = [
    # Staff - Payment Management
    path('payments/', views.staff_payments_view, name='staff_payments'),
    path('payments/verify/<int:payment_id>/', views.verify_payment_view, name='staff_verify_payment'),
    path('payments/cash-confirm/<int:payment_id>/', views.cash_payment_confirmation_view, name='staff_cash_payment_confirm'),
]
