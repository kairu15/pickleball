from django.contrib import admin
from .models import Equipment, EquipmentRental, EquipmentMaintenance


class EquipmentRentalInline(admin.TabularInline):
    model = EquipmentRental
    extra = 0


class EquipmentMaintenanceInline(admin.TabularInline):
    model = EquipmentMaintenance
    extra = 0


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'brand', 'quantity_available', 'quantity_total', 'rental_price', 'condition', 'is_active']
    list_filter = ['type', 'condition', 'is_active']
    search_fields = ['name', 'brand', 'description']
    inlines = [EquipmentRentalInline, EquipmentMaintenanceInline]


@admin.register(EquipmentRental)
class EquipmentRentalAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'rented_by', 'status', 'rented_at', 'returned_at', 'rental_fee']
    list_filter = ['status', 'rented_at']
    search_fields = ['equipment__name', 'rented_by__username']
