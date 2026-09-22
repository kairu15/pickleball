from django.urls import path
from . import views

urlpatterns = [
    # Super Admin - Payment & Revenue Management
    path('payments/', views.admin_payments_view, name='super_admin_payments'),
    path('payment-settings/', views.payment_settings_view, name='super_admin_payment_settings'),
    path('payments/cancellation-refunds/', views.admin_cancellation_refunds_view, name='super_admin_cancellation_refunds'),
    path('payments/verify/<int:payment_id>/', views.verify_payment_view, name='super_admin_verify_payment'),
    path('revenue/', views.revenue_report_view, name='super_admin_revenue_report'),
    path('revenue/export/', views.revenue_report_export_view, name='super_admin_revenue_report_export'),
]
