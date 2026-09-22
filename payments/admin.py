from django.contrib import admin
from .models import Payment, Refund, PaymentLog


class PaymentLogInline(admin.TabularInline):
    model = PaymentLog
    extra = 0
    readonly_fields = ['action', 'details', 'performed_by', 'created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'reservation', 'amount', 'status', 'method', 'created_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['reservation__user__username', 'transaction_id', 'gcash_reference']
    inlines = [PaymentLogInline]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'amount', 'status', 'requested_by', 'requested_at']
    list_filter = ['status', 'requested_at']
