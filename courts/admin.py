from django.contrib import admin
from .models import Site, Court, CourtAvailability, CourtImage, CourtMaintenanceBlock


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


class CourtAvailabilityInline(admin.TabularInline):
    model = CourtAvailability
    extra = 0


class CourtImageInline(admin.TabularInline):
    model = CourtImage
    extra = 4
    fields = ['image', 'alt_text', 'is_primary', 'order']


class CourtMaintenanceBlockInline(admin.TabularInline):
    model = CourtMaintenanceBlock
    extra = 0
    fields = ['block_type', 'reason', 'start_datetime', 'end_datetime', 'created_by']
    readonly_fields = ['created_by']
    show_change_link = True


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'court_type', 'status', 'hourly_rate', 'is_active']
    list_filter = ['site', 'court_type', 'status', 'is_active']
    search_fields = ['name', 'description']
    inlines = [CourtImageInline, CourtAvailabilityInline, CourtMaintenanceBlockInline]


@admin.register(CourtMaintenanceBlock)
class CourtMaintenanceBlockAdmin(admin.ModelAdmin):
    list_display = ['court', 'block_type', 'reason', 'start_datetime', 'end_datetime', 'created_by']
    list_filter = ['block_type', 'court']
    search_fields = ['reason', 'court__name']
    date_hierarchy = 'start_datetime'
