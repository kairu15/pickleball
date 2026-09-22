from django.contrib import admin
from .models import Site, Court, CourtAvailability, CourtImage


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


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'court_type', 'status', 'hourly_rate', 'is_active']
    list_filter = ['site', 'court_type', 'status', 'is_active']
    search_fields = ['name', 'description']
    inlines = [CourtImageInline, CourtAvailabilityInline]
